
# Relationship between modules

A -- >  B  --> D
  --->  C  --> D
  --->  only_Release_X64
  --->  only_Linux_Debug


C is a head only libs

# Dependencies of third-party libraries
D --> default_party
C --> default_party_only_include
B --> third_party1

Only A is a binary

# Case missing default fields

A lack of third_parties
D lack of dependencies