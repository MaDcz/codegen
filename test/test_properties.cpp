#include "properties.hpp"

#include <iostream>
#include <string>

int main(int argc, char* argv[])
{
  (void)argc;
  (void)argv;

  class TestCase
  {
  public:
    explicit TestCase(const std::string& name)
      : m_name(name)
    {
    }

    virtual ~TestCase()
    {
      std::cout << m_name << " ... ";
      if (m_failuresCount > 0)
      {
        std::cout << m_failuresCount << " failures.";
      }
      else
      {
        std::cout << "Passed.";
      }
      std::cout << std::endl;
    }

    void failure()
    {
      ++m_failuresCount;
    }

  private:
    std::string m_name;
    unsigned int m_failuresCount = 0;
  };

#define TEST_TRUE(maCond) \
  do \
  { \
    if (!(maCond)) \
    { \
      std::cout << "Test failure: '" << #maCond << "' not true." << std::endl; \
      testCase.failure(); \
    } \
  } \
  while (false)

#define TEST_FALSE(maCond) \
  do \
  { \
    if ((maCond)) \
    { \
      std::cout << "Test failure: '" << #maCond << "' not false." << std::endl; \
      testCase.failure(); \
    } \
  } \
  while (false)

  {
    TestCase testCase("CompositeNoPropertiesInitially");

    Type2 type2;

    TEST_FALSE(type2.type1_field);
    TEST_FALSE(type2.type1_field.isPresent());
    TEST_FALSE(type2.type1_list_field);
    TEST_FALSE(type2.type1_list_field.isPresent());

    TEST_TRUE(type2.empty());
    TEST_TRUE(type2.size() == 0);
  }

  {
    TestCase testCase("PropertyEnsureAndClear");

    Type1 type1;

    type1.int_field.ensure();

    TEST_TRUE(type1.int_field);
    TEST_TRUE(type1.int_field.isPresent());
    TEST_FALSE(type1.int_list_field);
    TEST_FALSE(type1.int_list_field.isPresent());

    TEST_TRUE(!type1.empty());
    TEST_TRUE(type1.size() == 1);

    type1.int_list_field.ensure();

    TEST_TRUE(type1.int_field);
    TEST_TRUE(type1.int_field.isPresent());
    TEST_TRUE(type1.int_list_field);
    TEST_TRUE(type1.int_list_field.isPresent());

    TEST_TRUE(!type1.empty());
    TEST_TRUE(type1.size() == 2);

    type1.int_field.clear();

    TEST_FALSE(type1.int_field);
    TEST_FALSE(type1.int_field.isPresent());
    TEST_TRUE(type1.int_list_field);
    TEST_TRUE(type1.int_list_field.isPresent());

    TEST_TRUE(!type1.empty());
    TEST_TRUE(type1.size() == 1);

    type1.int_list_field.clear();

    TEST_FALSE(type1.int_field);
    TEST_FALSE(type1.int_field.isPresent());
    TEST_FALSE(type1.int_list_field);
    TEST_FALSE(type1.int_list_field.isPresent());

    TEST_TRUE(type1.empty());
    TEST_TRUE(type1.size() == 0);

    Type2 type2;

    type2.type1_field.ensure();

    TEST_TRUE(type2.type1_field);
    TEST_TRUE(type2.type1_field.isPresent());
    TEST_FALSE(type2.type1_list_field);
    TEST_FALSE(type2.type1_list_field.isPresent());

    TEST_TRUE(!type2.empty());
    TEST_TRUE(type2.size() == 1);

    type2.type1_list_field.ensure();

    TEST_TRUE(type2.type1_field);
    TEST_TRUE(type2.type1_field.isPresent());
    TEST_TRUE(type2.type1_list_field);
    TEST_TRUE(type2.type1_list_field.isPresent());

    TEST_TRUE(!type2.empty());
    TEST_TRUE(type2.size() == 2);

    type2.type1_field.clear();

    TEST_FALSE(type2.type1_field);
    TEST_FALSE(type2.type1_field.isPresent());
    TEST_TRUE(type2.type1_list_field);
    TEST_TRUE(type2.type1_list_field.isPresent());

    TEST_TRUE(!type2.empty());
    TEST_TRUE(type2.size() == 1);

    type2.type1_list_field.clear();

    TEST_FALSE(type2.type1_field);
    TEST_FALSE(type2.type1_field.isPresent());
    TEST_FALSE(type2.type1_list_field);
    TEST_FALSE(type2.type1_list_field.isPresent());

    TEST_TRUE(type2.empty());
    TEST_TRUE(type2.size() == 0);
  }

  {
    TestCase testCase("CompositesAggregation");

    Type2 type2;

    TEST_TRUE(type2.empty());

    {
      auto& type1a = *type2.type1_field;

      TEST_TRUE(type2.size() == 1);

      auto& type1c = type2.type1_list_field.ensure(1);

      TEST_TRUE(type2.size() == 2);
      TEST_TRUE(type2.type1_list_field.size() == 2);

      auto& type1b = type2.type1_list_field[0];

      TEST_TRUE(type2.size() == 2);
      TEST_TRUE(type2.type1_list_field.size() == 2);

      TEST_TRUE(&type1a != &type1b);
      TEST_TRUE(&type1b != &type1c);
      TEST_TRUE(&type1c != &type1a);
    }

    type2.clear();

    TEST_TRUE(type2.empty());
  }

  return 0;

#undef TEST_TRUE
#undef TEST_FALSE
}
