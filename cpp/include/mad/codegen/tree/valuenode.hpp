#pragma once

#include <mad/interfaces/tree/node.hpp>

#include <type_traits>

namespace mad { namespace codegen { namespace tree {

template <typename TValue>
class ValueNode : public interfaces::tree::Node
{
public:
  using reference = typename std::conditional<std::is_fundamental<TValue>::value, TValue, TValue&>::type;
  using const_reference = typename std::conditional<std::is_fundamental<TValue>::value, TValue, const TValue&>::type;

public:
  template <typename TOtherValue>
  ValueNode& operator=(typename std::conditional<std::is_fundamental<TOtherValue>::value, TOtherValue, const TOtherValue&>::type otherValue)
  {
    m_value = otherValue;
    return *this;
  }

  const_reference get() const { return m_value; }

  void set(const_reference value) { m_value = value; }

private:
  TValue m_value = {};
};

}}} // namespace mad::codegen::tree
