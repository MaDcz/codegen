#pragma once

#include <mad/interfaces/tree/node.hpp>

#include <memory>

namespace mad { namespace codegen { namespace tree {

class Node : public virtual interfaces::tree::Node
{
public:
  Node() = default;

  Node(const Node&) = delete;
  Node& operator=(const Node&) = delete;

  Node(Node&&) = delete;
  Node& operator=(Node&&) = delete;
};

}}} // namespace mad::codegen::tree
