#ifndef __MAD_CODEGEN_COMPOSITESLISTPROPERTY_HPP__
#define __MAD_CODEGEN_COMPOSITESLISTPROPERTY_HPP__

#include "listproperty.hpp"

namespace mad { namespace codegen {

template <typename TCompositeNode>
class CompositesListProperty : public ListProperty<TCompositeNode>
{
private:
  using Base = ListProperty<TCompositeNode>;

public:
  CompositesListProperty(tree::CompositeNode& owningNode,
      const tree::CompositeNode::key_type& propKey)
    : Base(owningNode, propKey)
  {
  }
};

}} // namespace mad::codegen

#endif // __MAD_CODEGEN_COMPOSITESLISTPROPERTY_HPP__
