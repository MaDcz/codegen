#ifndef __MAD_CODEGEN_PROPERTY_H__
#define __MAD_CODEGEN_PROPERTY_H__

#include "tree.h"

#include <exception>

namespace mad { namespace codegen {

template <typename TNode>
class Property
{
public:
  Property(tree::CompositeNode& owningNode, const tree::CompositeNode::key_type& propKey)
    : m_owningNode(owningNode),
      m_propKey(propKey)
  {
  }

  ~Property()
  {
  }

  Property(const Property&) = delete;
  Property& operator=(const Property&) = delete;
  Property(Property&&) = delete;
  Property& operator=(Property&&) = delete;

  TNode* operator->() { return &ensureNode(); }
  const TNode* operator->() const { return &ensureNode(); }
  TNode& operator*() { return ensureNode(); }
  const TNode& operator*() const { return ensureNode(); }

  bool isPresent() const { return m_owningNode.find(m_propKey) != m_owningNode.end(); }
  explicit operator bool() const { return isPresent(); }
  TNode& ensure() { return ensureNode(); }

private:
  TNode& ensureNode()
  {
    auto it = m_owningNode.find(m_propKey);
    TNode* node = nullptr;
    if (it != m_owningNode.end())
    {
      node = dynamic_cast<TNode*>(&it->value());
    }
    else
    {
      auto insert = m_owningNode.insert(m_propKey, std::make_unique<TNode>());
      assert(insert.second);
      node = dynamic_cast<TNode*>(&insert.first->value());
    }

    assert(node);
    return *node;
  }

  const TNode& ensureNode() const
  {
    auto it = m_owningNode.find(m_propKey);
    const TNode* node = nullptr;
    if (it != m_owningNode.end())
    {
      node = dynamic_cast<const TNode*>(&it->value());
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

#endif // __MAD_CODEGEN_PROPERTY_H__
