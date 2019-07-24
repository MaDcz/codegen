#pragma once

#include <stdexcept>

namespace mad { namespace codegen {

template <typename TNode>
class ReferenceProperty
{
public:
  using Node = TNode;

public:
  ReferenceProperty() {}

  virtual ~ReferenceProperty() {}

  ReferenceProperty(const ReferenceProperty&) = delete;
  ReferenceProperty& operator=(const ReferenceProperty&) = delete;
  ReferenceProperty(ReferenceProperty&&) = delete;
  ReferenceProperty& operator=(ReferenceProperty&&) = delete;

  ReferenceProperty& operator=(const Node& node)
  {
    m_referencedNode = &node;
    return *this;
  }

  const Node* operator->() const { return &propertyNode(); }
  const Node& operator*() const { return propertyNode(); }

  bool isPresent() const { return m_referencedNode; }
  explicit operator bool() const { return isPresent(); }

protected:
  const Node& propertyNode() const
  {
    if (!m_referencedNode)
      throw std::logic_error("Cannot access null reference property.");

    return *m_referencedNode;
  }

private:
  const Node* m_referencedNode = nullptr;
};

}} // namespace mad::codegen
