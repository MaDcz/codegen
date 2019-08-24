#pragma once

#include "tree/compositenode.hpp"

#include <cassert>
#include <memory>
#include <stdexcept>

namespace mad { namespace codegen {

/**
 * @brief Base class for all property types.
 *
 * Properties provides quick access to explicitly declared data stored in the composite which owns
 * them.
 */
template <typename TNode>
class Property
{
public:
  using Node = TNode;

public:
  /**
   * @brief Initializes the property.
   *
   * @param owningNode The composite which owns this property.
   * @param propKey The key associated which this property.
   */
  Property(tree::CompositeNode& owningNode, const tree::CompositeNode::key_type& propKey)
    : m_owningNode(owningNode),
      m_propKey(propKey)
  {
  }

  // Properties are non-copyable and non-movable, there is nothing to copy or move, they
  // are providing typed data on the fly.

  Property(const Property&) = delete;
  Property& operator=(const Property&) = delete;

  Property(Property&&) = delete;
  Property& operator=(Property&&) = delete;

  virtual ~Property() {}

  Node* operator->() { return &ensurePropertyNode(); }
  const Node* operator->() const { return &propertyNode(); }
  Node& operator*() { return ensurePropertyNode(); }
  const Node& operator*() const { return propertyNode(); }

  bool isPresent() const { return m_owningNode.find(m_propKey) != m_owningNode.end(); }
  explicit operator bool() const { return isPresent(); }
  Node& ensure() { return ensurePropertyNode(); }
  Node& ensure(std::unique_ptr<Node>&& node) { return ensurePropertyNode(std::move(node)); }
  Node& ensure(Node&& node) { return ensurePropertyNode(std::move(node)); }
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

  Node& ensurePropertyNode(std::unique_ptr<Node>&& node = nullptr)
  {
    auto it = m_owningNode.find(m_propKey);

    if (it != m_owningNode.end() && node)
    {
      m_owningNode.erase(m_propKey);
      it = m_owningNode.end();
    }

    if (it == m_owningNode.end())
      it = m_owningNode.insert(m_propKey, node ? std::move(node) : std::make_unique<Node>()).first;

    auto storedNode = dynamic_cast<Node*>(&it->value());
    if (!storedNode)
      throw std::logic_error("Unexpected node type.");

    return *storedNode;
  }

  Node& ensurePropertyNode(Node&& node)
  {
    auto& storedNode = ensurePropertyNode();
    storedNode = std::move(node);
    return storedNode;
  }

private:
  tree::CompositeNode& m_owningNode;
  const tree::CompositeNode::key_type m_propKey;
};

}} // namespace mad::codegen
