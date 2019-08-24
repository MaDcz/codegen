#pragma once

#include <vector>

namespace mad { namespace codegen {

template <typename ItemNodeT>
class ReferencesListProperty
{
public:
  using ItemNode = ItemNodeT;

public:
  ReferencesListProperty() {}

  virtual ~ReferencesListProperty() {}

  const ItemNode& operator[](size_t pos) const { return *m_referencedNodes[pos]; }

  size_t size() const { return m_referencedNodes.size(); }

  bool isItemPresent(size_t pos) const { return pos < m_referencedNodes.size(); }

  void add(const ItemNode& node) { m_referencedNodes.push_back(&node); }

private:
  std::vector<const ItemNode*> m_referencedNodes;
};

}} // namespace mad::codegen
