#ifndef __MAD_CODEGEN_LISTPROPERTY_HPP__
#define __MAD_CODEGEN_LISTPROPERTY_HPP__

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

  using Base::ensure;

  ItemNode& ensure(size_t pos) { return ensureNode(pos); }

  ItemNode& operator[](size_t pos) { return node(pos); }

  const ItemNode& operator[](size_t pos) const { return node(pos); }

  size_t size() const { return node().size(); }

  using Base::isPresent;

  bool isPresent(size_t pos) const
  {
    return isPresent() && pos < node().size();
  }

protected:
  using Base::node;

  ItemNode& node(size_t pos)
  {
    auto& generalItemNode = node().at(pos);
    auto itemNode = dynamic_cast<ItemNode*>(&generalItemNode);
    if (!itemNode)
      throw std::logic_error("Invalid item type in list property at pos TODO.");

    return *itemNode;
  }

  const ItemNode& node(size_t pos) const
  {
    const auto& generalItemNode = node().at(pos);
    auto itemNode = dynamic_cast<const ItemNode*>(&generalItemNode);
    if (!itemNode)
      throw std::logic_error("Invalid item type in list property at pos TODO.");

    return *itemNode;
  }

  using Base::ensureNode;

  ItemNode& ensureNode(size_t pos)
  {
    auto& listNode = ensureNode();
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

#endif // __MAD_CODEGEN_LISTPROPERTY_HPP__
