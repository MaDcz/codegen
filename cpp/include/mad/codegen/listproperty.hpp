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

  ItemNode& ensure(size_t pos) { return ensureItemNode(pos); }

  ItemNode& operator[](size_t pos) { return itemNode(pos); }

  const ItemNode& operator[](size_t pos) const { return itemNode(pos); }

  size_t size() const { return itemNode().size(); }

  bool isItemPresent(size_t pos) const { return isPresent() && pos < itemNode().size(); }

protected:
  ItemNode& itemNode(size_t pos)
  {
    auto& generalItemNode = itemNode().at(pos);
    auto itemNode = dynamic_cast<ItemNode*>(&generalItemNode);
    if (!itemNode)
      throw std::logic_error("Invalid item type in list property at pos TODO.");

    return *itemNode;
  }

  const ItemNode& itemNode(size_t pos) const
  {
    const auto& generalItemNode = itemNode().at(pos);
    auto itemNode = dynamic_cast<const ItemNode*>(&generalItemNode);
    if (!itemNode)
      throw std::logic_error("Invalid item type in list property at pos TODO.");

    return *itemNode;
  }

  ItemNode& ensureItemNode(size_t pos)
  {
    auto& listNode = ensurePropertyNode();
    while (pos >= listNode.size())
      listNode.add(std::make_unique<ItemNode>());

    assert(pos < listNode.size());
    auto& generalItemNode = listNode[pos];
    auto itemNode = dynamic_cast<ItemNode*>(&generalItemNode);
    if (!itemNode)
      throw std::logic_error("Invalid item type in list property at pos TODO.");

    return *itemNode;
  }
};

}} // namespace mad::codegen
