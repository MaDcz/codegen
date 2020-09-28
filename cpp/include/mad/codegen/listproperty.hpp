#pragma once

#include "property.hpp"

#include <mad/interfaces/tree/listnode.hpp>

#include <stdexcept>

namespace mad { namespace codegen {

template <typename TItemNode>
class ListProperty : public Property<interfaces::tree::ListNode>
{
public:
  using ItemNode = TItemNode;

private:
  using Base = Property<interfaces::tree::ListNode>;

public:
  ListProperty(tree::CompositeNode& owningNode, const tree::CompositeNode::key_type& propKey)
    : Base(owningNode, propKey)
  {
  }

  ItemNode& addItem();

  void addItem(std::unique_ptr<ItemNode>&& itemNode);

  ItemNode& ensureItem(size_t pos);

  void ensureItem(size_t pos, std::unique_ptr<ItemNode>&& itemNode);

  ItemNode& operator[](size_t pos) { return itemNode(pos); }

  const ItemNode& operator[](size_t pos) const { return itemNode(pos); }

  size_t size() const { return isPresent() ? propertyNode().size() : 0; }

  bool isItemPresent(size_t pos) const { return isPresent() && pos < propertyNode().size(); }

  size_t indexOf(const ItemNode& itemNode) const;

protected:
  ItemNode& itemNode(size_t pos)
  {
    auto& generalItemNode = propertyNode().at(pos);
    auto itemNode = dynamic_cast<ItemNode*>(&generalItemNode);
    if (!itemNode)
      throw std::logic_error("Invalid item type in list property at pos TODO.");

    return *itemNode;
  }

  const ItemNode& itemNode(size_t pos) const
  {
    const auto& generalItemNode = propertyNode().at(pos);
    auto itemNode = dynamic_cast<const ItemNode*>(&generalItemNode);
    if (!itemNode)
      throw std::logic_error("Invalid item type in list property at pos TODO.");

    return *itemNode;
  }

  ItemNode& ensureItemNode(size_t pos, std::unique_ptr<ItemNode>&& itemNode = nullptr);
};

template <typename TItemNode>
inline TItemNode& ListProperty<TItemNode>::addItem()
{
  return ensureItemNode(size());
}

template <typename TItemNode>
inline void ListProperty<TItemNode>::addItem(std::unique_ptr<ItemNode>&& itemNode)
{
  ensureItemNode(size(), std::move(itemNode));
}

template <typename TItemNode>
inline TItemNode& ListProperty<TItemNode>::ensureItem(size_t pos)
{
  return ensureItemNode(pos);
}

template <typename TItemNode>
inline void ListProperty<TItemNode>::ensureItem(size_t pos, std::unique_ptr<ItemNode>&& itemNode)
{
  ensureItemNode(pos, std::move(itemNode));
}

template <typename TItemNode>
size_t ListProperty<TItemNode>::indexOf(const ItemNode& itemNode) const
{
  for (size_t index = 0; index < size(); ++index)
      if (&this->itemNode(index) == &itemNode)
          return index;

  throw std::logic_error("Provided item isn't in this list.");
}

template <typename TItemNode>
inline TItemNode& ListProperty<TItemNode>::ensureItemNode(size_t pos,
    std::unique_ptr<ItemNode>&& itemNode)
{
  auto& listNode = ensurePropertyNode();
  while (pos > listNode.size())
    listNode.add(std::make_unique<ItemNode>());

  if (pos == listNode.size())
  {
    // The item doesn't exist yet, add new node to the list.
    if (!itemNode)
      itemNode.reset(new ItemNode);
    auto& itemNodeRef = *itemNode.get();
    listNode.add(std::move(itemNode));
    return itemNodeRef;
  }
  else if (itemNode)
  {
    // We have to replace the existing item node with the new one.
    assert(pos < listNode.size());
    listNode.erase(pos);
    auto& itemNodeRef = *itemNode.get();
    listNode.insert(pos, std::move(itemNode));
    return itemNodeRef;
  }
  else
  {
    // Return the existing item node.
    assert(pos < listNode.size());
    auto& generalItemNode = listNode[pos];
    auto itemNode = dynamic_cast<ItemNode*>(&generalItemNode);
    if (!itemNode)
      throw std::logic_error("Invalid item type in list property at pos TODO.");

    return *itemNode;
  }
}

}} // namespace mad::codegen
