#ifndef __MAD_CODEGEN_TREE_HPP__
#define __MAD_CODEGEN_TREE_HPP__

#include <mad/interfaces/tree.hpp>

namespace mad { namespace codegen { namespace tree {

class CompositeNode : public interfaces::tree::MapNode
{
};

template <typename T>
class ValueNode : public interfaces::tree::Node
{
};

class IntegerNode : public ValueNode<int>
{
};

class FloatNode : public ValueNode<float>
{
};

}}} // namespace mad::codegen::tree

#endif // __MAD_CODEGEN_TREE_HPP__
