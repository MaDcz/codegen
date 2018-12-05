#ifndef __MAD_CODEGEN_VALUEPROPERTY_HPP__
#define __MAD_CODEGEN_VALUEPROPERTY_HPP__

#include "property.hpp"
#include "tree/valuenode.hpp"

namespace mad { namespace codegen {

template <typename TValue>
class ValueProperty : public Property<tree::ValueNode<TValue>>
{
public:
  ValueProperty(tree::CompositeNode& owningNode, const tree::CompositeNode::key_type& propKey)
    : Property<tree::ValueNode<TValue>>(owningNode, propKey)
  {
  }

  template <typename TOtherValueProperty>
  ValueProperty& operator=(const TOtherValueProperty& other)
  {
    if (other)
      this->ensureNode() = other->get();

    return *this;
  }
};

}} // namespace mad::codegen

#endif // __MAD_CODEGEN_VALUEPROPERTY_HPP__
