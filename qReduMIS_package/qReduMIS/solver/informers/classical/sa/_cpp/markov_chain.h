// SPDX-License-Identifier: Apache-2.0
// Copyright 2023: Amazon Web Services, Inc
//
// This file contains an implementation of a Monte-Carlo Markov chain.
#pragma once

#include <cmath>

#include "independent_set.h"
#include "random.h"

class MarkovChain {
public:
  // Create an empty chain and reset all its fields.
  MarkovChain()
      : model(nullptr), rng(nullptr), beta(1.0), n_moves(0), n_accepted(0) {}

  // Set the model to be simulated.
  void set_model(const IndependentSet *model) { this->model = model; }

  // Set the random number generator to use for updates.
  // Must be dedicated per thread (no concurrency checks performed)
  void set_rng(Rng *rng) { this->rng = rng; }

  // Set the inverse temperature to use for updates (beta = 1/T).
  void set_beta(double beta) { this->beta = beta; }

  // Initialize the chain with a state from the model and calculate its
  // starting cost. Whether this initial state is random is decided by the
  // model.
  void init() {
    state = model->get_initial_state(*rng);
    cost = model->cost(state);
    best_state = state;
    best_cost = cost;
  }

  // Whether to accept a specific update.
  // Only called for positive values of diff (i.e., when the change would
  // increase the cost). All other moves are accepted greedily.
  // NOTE: For discrete models, we could speed things up further by
  // pre-computing a lookup table for the exp values -- exp is slow.
  bool accept(double diff) { return rng->uniform() < exp(-diff * beta); }

  // Perform a "sweep" which consists of `N` random updates (one per variable
  // on average).
  void make_sweep() {
    for (int i = 0; i < model->N; i++) {
      // Let the model create a random move
      Move move = model->get_random_move(state, *rng);
      n_moves++; // counting statistics
      double diff = model->cost_diff(state, move);
      // The move does not increase the cost -- always accept
      if (diff <= 0) {
        model->apply_move(state, move);
        cost += diff;
        if (cost < best_cost) {
          // The move decreases the cost -- update lowest value.
          best_state = state;
          best_cost = cost;
        }
        n_accepted++; // acceptance statistics
      } else if (accept(diff)) {
        model->apply_move(state, move);
        cost += diff;
        n_accepted++; // acceptance statistics
      }
      // sanity check that our updated cost corresponds to the result of
      // evaluating the entire cost function. This is slow by design, but
      // assert is removed when NDEBUG is set (see Makefile).
      assert(abs(model->cost(state) - cost) < 1e-6);
    }
  }

  const IndependentSet *model;
  Rng *rng;
  double beta;
  State state;
  double cost;
  State best_state;
  double best_cost;
  uint64_t n_moves;
  uint64_t n_accepted;
};
