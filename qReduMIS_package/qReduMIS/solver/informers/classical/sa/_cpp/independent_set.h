// SPDX-License-Identifier: Apache-2.0
// Copyright 2023: Amazon Web Services, Inc
//
// This file implements an independent set model on the Union-Jack lattice,
// which considers only valid states (without violations of the independence
// criterion) and biases move selection towards filling vacant nodes and
// performing exchange moves over node removal.
#pragma once

#include <queue>
using std::queue;

#include "instance.h"
#include "random.h"
#include "state.h"

class IndependentSet {
public:
  // Load an instance from a METIS file
  //
  // This converts the 1-index adjacency list to a 0-indexed one.
  void load_instance(const string &filename) {
    Instance instance;
    instance.load(filename);
    N = instance.N;
    neighbors.resize(N);
    for (int i = 0; i < N; i++) {
      neighbors[i].resize(instance.adj[i + 1].size());
      for (int j = 0; j < neighbors[i].size(); j++) {
        neighbors[i][j] = instance.adj[i + 1][j] - 1;
      }
    }
  }

  // Create initial states
  //
  // We maximize the initial state w.r.t. node addition by processing all nodes
  // in a random order and adding each if it still has no neighbors in the set.
  // (i.e., this drives the state to a local maximum in terms of the number
  // of nodes in the set).
  State get_initial_state(Rng &rng) const {
    State state(N);
    vector<uint32_t> indices(N);
    for (int i = 0; i < N; i++)
      indices[i] = i;
    std::shuffle(indices.begin(), indices.end(), rng);
    for (auto i : indices) {
      if (state.adjacent[i] == 0)
        state.add(i, neighbors[i]);
    }
    return state;
  }

  // Propose a random move
  Move get_random_move(const State &state, Rng &rng) const {
    // 60% chance to propose a node addition if a vacant node_id exists.
    double r = rng.uniform();
    if (state.vacant > state.size) {
      if (r < 0.6) {
        // Nodes at a position [state.size, state.vacant) are guaranteed to
        // have no neighbors currently in the set (can be added).
        Position p = state.size + (state.vacant - state.size) * r / 0.6;
        return {state.order[p], NO_MOVE};
      }
      r = (r - 0.6) / 0.4; // rescale r to [0,1)
    }

    // 60% of _remaining_ probability: propose an exchange move if one exists
    // Potential exchange moves are uniquely identified by sites with only a
    // single neighbor currently in the set.
    if (state.single > state.vacant) {
      if (r < 0.6) {
        // Nodes at a position [state.vacant, state.single) are guaranteed to
        // have exactly one neighbor currently in the set (can be exchanged).
        Position p = state.vacant + (state.single - state.vacant) * r / 0.6;
        NodeId i = state.order[p];
        // Find the unique neighbor in the set.
        for (int j : neighbors[i]) {
          if (state.in_set[j])
            return {j, i};
        }
      }
      r = (r - 0.6) / 0.4; // rescale r to [0,1)
    }

    // With remaining probability, propose removing a node from the set.
    if (state.size) {
      // Nodes at position [0, state.size) are guaranteed to currently be in
      // the set.
      Position p = state.size * r;
      return {state.order[p], NO_MOVE};
    }

    // We didn't hit probabilities for an addition or exchange AND the
    // independent set is currently empty; therefore we can't propose an
    // addition. In this extremely rare case, do nothing.
    return {NO_MOVE, NO_MOVE};
  }

  // Toggle an individual node (unless it is NO_MOVE)
  void flip_node(State &state, const NodeId i) const {
    if (i == NO_MOVE)
      return;
    if (state.in_set[i])
      state.remove(i, neighbors[i]);
    else
      state.add(i, neighbors[i]);
  }

  // Apply a move to a pair of nodes (flip each, unless it is NO_MOVE)
  void apply_move(State &state, const Move &move) const {
    flip_node(state, move.first);
    flip_node(state, move.second);
  }

  // Cost function
  //
  // We define the cost function for the independent set model as minus the
  // number of nodes in the current independent set (simulated annealing is
  // implemented to find the lowest cost state).
  double cost(const State &state) const {
    double size = 0;
    for (NodeId i = 0; i < N; i++) {
      if (state.in_set[i])
        size++;
    }
    return -size;
  }

  // Locally calculate the change in cost for a move
  double cost_diff(const State &state, const Move &move) const {
    if (move.second != NO_MOVE) {
      // If move.second is set, this is an exchange which always has zero
      // cost (we propose only exchanges where one is in the set and the other
      // is not).
      return 0.0;
    } else if (move.first == NO_MOVE) {
      // If move.first is not set, this is no-op.
      assert(move.second == NO_MOVE);
      return 0.0;
    } else {
      // The remaining cases are removal and addition, which we distinguish
      // according to whether the target node is currently in the set. If it
      // is, we are removing and the cost increases (because cost = - #in_set)
      // otherwise we are adding and it decreases.
      return state.in_set[move.first] ? 1 : -1;
    }
  }

  int N;                            // The number of nodes in the instance
  vector<vector<NodeId>> neighbors; // 0-index adjacency list.
};
