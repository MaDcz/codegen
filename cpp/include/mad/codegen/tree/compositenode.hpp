#pragma once

#include "node.hpp"

#include <mad/interfaces/tree/mapnode.hpp>

#include <assert.h>

namespace mad { namespace codegen { namespace tree {

class CompositeNode : public Node,
                      public interfaces::tree::MapNode
{
public:
  CompositeNode() = default;

  CompositeNode(const CompositeNode& other)
  {
    other.copyContentInto(*this);
  }

  CompositeNode& operator=(const CompositeNode& other)
  {
    clear();
    other.copyContentInto(*this);
    return *this;
  }

  std::unique_ptr<Node> clone() const override
  {
    auto node = std::make_unique<CompositeNode>();
    copyContentInto(*node);
    return node;
  }

private:
  void copyContentInto(CompositeNode& dest) const
  {
    for (const auto& item : *this)
    {
      auto clonableChildNode = dynamic_cast<const Node*>(&item.value());
      assert(clonableChildNode);
      dest.insert(item.key(), clonableChildNode->clone());
    }
  }
};

}}} // namespace mad::codegen::tree
