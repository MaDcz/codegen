#ifndef __MAD_CODEGEN_COMPOSITESLISTPROPERTY_HPP__
#define __MAD_CODEGEN_COMPOSITESLISTPROPERTY_HPP__

#include "tree.hpp"

#include <exception>

namespace mad { namespace codegen {

template <typename TNode>
class CompositesListProperty
{
public:
  using Node = TNode;

public:
  CompositesListProperty(tree::CompositeNode& owningNode, const tree::CompositeNode::key_type& propKey)
    : m_owningNode(owningNode),
      m_propKey(propKey)
  {
  }

  ~CompositesListProperty()
  {
  }

  CompositesListProperty(const CompositesListProperty&) = delete;
  CompositesListProperty& operator=(const CompositesListProperty&) = delete;
  CompositesListProperty(CompositesListProperty&&) = delete;
  CompositesListProperty& operator=(CompositesListProperty&&) = delete;

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

#endif // __MAD_CODEGEN_COMPOSITESLISTPROPERTY_HPP__
