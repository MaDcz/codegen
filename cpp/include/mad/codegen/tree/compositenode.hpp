#pragma once

#include "node.hpp"

#include <mad/interfaces/tree/mapnode.hpp>

#include <assert.h>

namespace mad { namespace codegen { namespace tree {

class CompositeNode : public Node,
                      public interfaces::tree::MapNode
{
};

}}} // namespace mad::codegen::tree
