#include <iostream>
#include <fstream>

#ifdef _DEBUG
#include "only_debug/include.h"
#else
#include "only_release/include.h"
#endif

#include "default_party/default_party.h"
#include "head_only/head_only.h"

using namespace std;

int main() {
    cout<<"Hello world! Pointer size is "<< sizeof(void*) << endl;
    cout << "Configuration is " << output_configuration() << endl;
#ifndef _DEBUG
    cout << "default party test " << test_default_party() << endl;
#endif
    head_only::func<3>(233);
}