#ifndef __MAD_CODEGEN_PROPERTY_HPP__
#define __MAD_CODEGEN_PROPERTY_HPP__

#include "tree/compositenode.hpp"

#include <cassert>
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

  Node* operator->() { return &ensureNode(); }
  const Node* operator->() const { return &node(); }
  Node& operator*() { return ensureNode(); }
  const Node& operator*() const { return node(); }

  bool isPresent() const { return m_owningNode.find(m_propKey) != m_owningNode.end(); }
  explicit operator bool() const { return isPresent(); }
  Node& ensure() { return ensureNode(); }
  void clear() { m_owningNode.erase(m_propKey); }

protected:
  Node& node()
  {
    auto it = m_owningNode.find(m_propKey);
    Node* node = nullptr;
    if (it != m_owningNode.end())
      node = dynamic_cast<Node*>(&it->value());
    else
      throw std::logic_error("Property not present in the owning composite.");

    assert(node);
    return *node;
  }

  const Node& node() const
  {
    auto it = m_owningNode.find(m_propKey);
    const Node* node = nullptr;
    if (it != m_owningNode.end())
      node = dynamic_cast<const Node*>(&it->value());
    else
      throw std::logic_error("Property not present in the owning composite.");

    assert(node);
    return *node;
  }

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

private:
  tree::CompositeNode& m_owningNode;
  const tree::CompositeNode::key_type m_propKey;
};

}} // namespace mad::codegen

#endif // __MAD_CODEGEN_PROPERTY_HPP__
