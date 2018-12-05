#ifndef __MAD_CODEGEN_VALUESLISTPROPERTY_HPP__
#define __MAD_CODEGEN_VALUESLISTPROPERTY_HPP__

#include "listproperty.hpp"
#include "tree/valuenode.hpp"

namespace mad { namespace codegen {

template <typename TValue>
class ValuesListProperty : public ListProperty<tree::ValueNode<TValue>>
{
private:
  using Base = ListProperty<tree::ValueNode<TValue>>;

public:
  ValuesListProperty(tree::CompositeNode& owningNode, const tree::CompositeNode::key_type& propKey)
    : Base(owningNode, propKey)
  {
  }
};

}} // namespace mad::codegen

#endif // __MAD_CODEGEN_VALUESLISTPROPERTY_HPP__
