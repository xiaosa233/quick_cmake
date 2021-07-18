
#include <iostream>
#include <string>

namespace head_only{

template<size_t N>
void func(int x) {
  printf("from head only : %d \n", x + N);
}

}