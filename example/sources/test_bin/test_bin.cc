#include <iostream>
#include <fstream>

#ifdef _DEBUG
#include "only_debug/include.h"
#else
#include "only_release/include.h"
#endif

#include "default_party.h"

using namespace std;

int main() {
    cout<<"Hello world! Pointer size is "<< sizeof(void*) << endl;
    cout << "Configuration is " << output_configuration() << endl;
#ifndef _DEBUG
    cout << "default party test " << test_default_party() << endl;
#endif
}