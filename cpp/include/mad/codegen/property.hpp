#pragma once

#include "tree/compositenode.hpp"

#include <cassert>
#include <memory>
#include <stdexcept>

namespace mad { namespace codegen {

template <typename TNode>
class Property
{
public:
  using Node = TNode;

public:
  Property(tree::CompositeNode& owningNode, const tree::CompositeNode::key_type& propKey)
    : m_owningNode(owningNode),
      m_propKey(propKey)
  {
  }

  virtual ~Property()
  {
  }

  Property(const Property&) = delete;
  Property& operator=(const Property&) = delete;
  Property(Property&&) = delete;
  Property& operator=(Property&&) = delete;

  Node* operator->() { return &ensurePropertyNode(); }
  const Node* operator->() const { return &propertyNode(); }
  Node& operator*() { return ensurePropertyNode(); }
  const Node& operator*() const { return propertyNode(); }

  bool isPresent() const { return m_owningNode.find(m_propKey) != m_owningNode.end(); }
  explicit operator bool() const { return isPresent(); }
  Node& ensure() { return ensurePropertyNode(); }
  void clear() { m_owningNode.erase(m_propKey); }

protected:
  const Node& propertyNode() const
  {
    auto it = m_owningNode.find(m_propKey);
    if (it == m_owningNode.end())
      throw std::logic_error("Null property access violation.");

    auto node = dynamic_cast<const Node*>(&it->value());
    if (!node)
      throw std::logic_error("Unexpected node type.");

    return *node;
  }

  Node& ensurePropertyNode()
  {
    auto it = m_owningNode.find(m_propKey);
    if (it == m_owningNode.end())
      it = m_owningNode.insert(m_propKey, std::make_unique<Node>()).first;

    auto node = dynamic_cast<Node*>(&it->value());
    if (!node)
      throw std::logic_error("Unexpected node type.");

    return *node;
  }

private:
  tree::CompositeNode& m_owningNode;
  const tree::CompositeNode::key_type m_propKey;
};

}} // namespace mad::codegen
