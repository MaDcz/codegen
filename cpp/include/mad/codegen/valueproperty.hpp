#pragma once

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

  ValueProperty& operator=(const ValueProperty& other)
  {
    if (other)
      this->ensure() = other->get();
    else
      this->clear();

    return *this;
  }

  ValueProperty& operator=(typename tree::ValueNode<TValue>::const_reference otherValue)
  {
    this->ensure() = otherValue;
    return *this;
  }

  bool operator==(const ValueProperty& other) const
  {
    auto thisPresent = this->isPresent();
    auto otherPresent = other.isPresent();

    if (thisPresent != otherPresent)
      return false;
    else if (!thisPresent)
      return true;
    else
      return propertyNode() == other.propertyNode();
  }

  bool operator!=(const ValueProperty& other) const
  {
    return !this->operator==(other);
  }

  bool operator==(typename tree::ValueNode<TValue>::const_reference otherValue) const
  {
    if (!this->isPresent())
      return false;
    else
      return propertyNode().get() == otherValue;
  }

  bool operator!=(typename tree::ValueNode<TValue>::const_reference otherValue) const
  {
    return !this->operator==(otherValue);
  }
};

}} // namespace mad::codegen
