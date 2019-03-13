#pragma once

#include <mad/interfaces/tree/node.hpp>

#include <memory>

namespace mad { namespace codegen { namespace tree {

class Node : public virtual mad::interfaces::tree::Node
{
public:
    virtual std::unique_ptr<Node> clone() const = 0;
};

}}} // namespace mad::codegen::tree
