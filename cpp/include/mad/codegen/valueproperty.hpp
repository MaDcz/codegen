#ifndef __MAD_CODEGEN_VALUEPROPERTY_HPP__
#define __MAD_CODEGEN_VALUEPROPERTY_HPP__

#include "tree.hpp"

#include <exception>

namespace mad { namespace codegen {

template <typename TNode>
class ValueProperty
{
public:
  using Node = TNode;

public:
  ValueProperty(tree::CompositeNode& owningNode, const tree::CompositeNode::key_type& propKey)
    : m_owningNode(owningNode),
      m_propKey(propKey)
  {
  }

  ~ValueProperty()
  {
  }

  ValueProperty(const ValueProperty&) = delete;
  ValueProperty& operator=(const ValueProperty&) = delete;
  ValueProperty(ValueProperty&&) = delete;
  ValueProperty& operator=(ValueProperty&&) = delete;

  Node* operator->() { return &ensureNode(); }
  const Node* operator->() const { return &ensureNode(); }
  Node& operator*() { return ensureNode(); }
  const Node& operator*() const { return ensureNode(); }

  bool isPresent() const { return m_owningNode.find(m_propKey) != m_owningNode.end(); }
  explicit operator bool() const { return isPresent(); }
  Node& ensure() { return ensureNode(); }

private:
  Node& ensureNode()
  {
    auto it = m_owningNode.find(m_propKey);
    Node* node = nullptr;
    if (it != m_owningNode.end())
    {
      node = dynamic_cast<Node*>(&it->value());
    }
    else
    {
      auto insert = m_owningNode.insert(m_propKey, std::make_unique<Node>());
      assert(insert.second);
      node = dynamic_cast<Node*>(&insert.first->value());
    }

    assert(node);
    return *node;
  }

  const Node& ensureNode() const
  {
    auto it = m_owningNode.find(m_propKey);
    const Node* node = nullptr;
    if (it != m_owningNode.end())
    {
      node = dynamic_cast<const Node*>(&it->value());
    }
    else
    {
      throw std::logic_error("Property not present in the owning composite.");
    }

    assert(node);
    return *node;
  }

private:
  tree::CompositeNode& m_owningNode;
  const tree::CompositeNode::key_type m_propKey;
};

}} // namespace mad::codegen

#endif // __MAD_CODEGEN_VALUEPROPERTY_HPP__
