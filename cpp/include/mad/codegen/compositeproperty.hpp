#pragma once

#include "property.hpp"

namespace mad { namespace codegen {

template <typename TComposite>
class CompositeProperty : public Property<TComposite>
{
public:
  CompositeProperty(tree::CompositeNode& owningNode, const tree::CompositeNode::key_type& propKey)
    : Property<TComposite>(owningNode, propKey)
  {
  }
};

}} // namespace mad::codegen
