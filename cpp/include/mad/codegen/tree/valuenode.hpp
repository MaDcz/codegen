#ifndef __MAD_CODEGEN_TREE_VALUENODE_HPP__
#define __MAD_CODEGEN_TREE_VALUENODE_HPP__

#include <mad/interfaces/tree/node.hpp>

namespace mad { namespace codegen { namespace tree {

template <typename TValue>
class ValueNode : public interfaces::tree::Node
{
public:
  template <typename TOtherValue>
  ValueNode& operator=(TOtherValue otherValue)
  {
    m_value = otherValue;
    return *this;
  }

  TValue get() const { return m_value; }

  void set(TValue value) { m_value = value; }

private:
  TValue m_value = {};
};

}}} // namespace mad::codegen::tree

#endif // __MAD_CODEGEN_TREE_VALUENODE_HPP__
