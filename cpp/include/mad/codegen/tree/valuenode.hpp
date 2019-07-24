#pragma once

#include "node.hpp"

#include <type_traits>

namespace mad { namespace codegen { namespace tree {

template <typename TValue>
class ValueNode : public Node
{
public:
  using reference = typename std::conditional<std::is_fundamental<TValue>::value, TValue, TValue&>::type;
  using const_reference = typename std::conditional<std::is_fundamental<TValue>::value, TValue, const TValue&>::type;

public:
// FIXME Could be used for any compatible value type.
//  template <typename TOtherValue>
//  ValueNode& operator=(typename std::conditional<std::is_fundamental<TOtherValue>::value, TOtherValue, const TOtherValue&>::type otherValue)
//  {
//    m_value = otherValue;
//    return *this;
//  }

  ValueNode& operator=(const_reference value)
  {
    m_value = value;
    return *this;
  }

  reference get() { return m_value; }

  const_reference get() const { return m_value; }

  void set(const_reference value) { m_value = value; }

  operator reference() { return m_value; }

  operator const_reference() const { return m_value; }

  bool operator==(const ValueNode& other) const
  {
    return m_value == other.m_value;
  }

  bool operator!=(const ValueNode& other) const
  {
    return !this->operator==(other);
  }

private:
  TValue m_value = {};
};

}}} // namespace mad::codegen::tree
