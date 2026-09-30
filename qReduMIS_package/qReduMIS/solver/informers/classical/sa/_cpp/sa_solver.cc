// SPDX-License-Identifier: Apache-2.0
// Copyright 2025: Amazon Web Services, Inc
//
// SA solver that outputs ALL replica solutions as JSON for Python integration.
// Usage: sa_solver [file] [replicas] [steps] [b_min] [b_max] [seed]
//
// Output format (JSON to stdout):
// {"solutions": [{"nodes": [0, 2, 4], "size": 3}, ...], "best_size": 3}

#include <string>
using std::string;

#include <iostream>
using std::cout;
using std::endl;

#include <sstream>
#include <vector>

#include "independent_set.h"
#include "markov_chain.h"

int main(int argc, char *argv[]) {
  if (argc < 2) {
    std::cerr << "Usage: " << argv[0]
              << " [file] [replicas] [steps] [b_min] [b_max] [seed]" << endl;
    return 1;
  }

  string file = argv[1];
  int replicas = argc > 2 ? atoi(argv[2]) : 10000;
  int steps = argc > 3 ? atoi(argv[3]) : 32;
  double b_min = argc > 4 ? atof(argv[4]) : 1e1;
  double b_max = argc > 5 ? atof(argv[5]) : 5e3;
  int seed = argc > 6 ? atoi(argv[6]) : 0;

  IndependentSet model;
  model.load_instance(file);

  // Collect best state from each replica
  struct Solution {
    std::vector<int> nodes;
    int size;
  };

  std::vector<Solution> all_solutions;
  int global_best = 0;

  for (int r = 0; r < replicas; r++) {
    MarkovChain chain;
    Rng rng(seed + r);
    chain.set_model(&model);
    chain.set_rng(&rng);
    chain.init();

    for (int s = 0; s < steps; s++) {
      double frac = (steps > 1) ? static_cast<double>(s) / (steps - 1) : 1.0;
      double beta = b_min + frac * (b_max - b_min);
      chain.set_beta(beta);
      chain.make_sweep();
    }

    // Collect best state from this replica
    Solution sol;
    for (int i = 0; i < model.N; i++) {
      if (chain.best_state.in_set[i]) {
        sol.nodes.push_back(i);
      }
    }
    sol.size = sol.nodes.size();
    if (sol.size > global_best)
      global_best = sol.size;
    all_solutions.push_back(sol);
  }

  // Output JSON
  cout << "{\"solutions\": [";
  for (size_t i = 0; i < all_solutions.size(); i++) {
    if (i > 0)
      cout << ", ";
    cout << "{\"nodes\": [";
    for (size_t j = 0; j < all_solutions[i].nodes.size(); j++) {
      if (j > 0)
        cout << ", ";
      cout << all_solutions[i].nodes[j];
    }
    cout << "], \"size\": " << all_solutions[i].size << "}";
  }
  cout << "], \"best_size\": " << global_best << "}" << endl;

  return 0;
}
