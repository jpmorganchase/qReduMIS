######################################################################
# // SPDX-License-Identifier: Apache-2.0
# // Copyright 2025: Amazon Web Services, Inc
######################################################################
#
# Builds the `sa_solver` binary used by the qReduMIS SA informer
# (qReduMIS/solver/informers/classical/sa/informer.py).
#
# Usage:
#   make          # build sa_solver
#   make clean    # remove the binary

CC       = g++
CPPFLAGS = -DNDEBUG -O3 -fomit-frame-pointer -std=c++11

SA_HEADERS = independent_set.h markov_chain.h instance.h state.h \
             random.h pcg_random.hpp pcg_extras.hpp

default: sa_solver

sa_solver: sa_solver.cc $(SA_HEADERS)
	$(CC) $(CPPFLAGS) -o $@ sa_solver.cc

clean:
	rm -f sa_solver

.PHONY: default clean
