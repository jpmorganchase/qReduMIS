// SPDX-License-Identifier: Apache-2.0
// Copyright 2023: Amazon Web Services, Inc
//
// This file contains a state representation for the independent set model.
// A state represents exactly one configuration (set of nodes chosen to be
// in the independent set).

#pragma once

#include <cstdint>
#include <vector>
using std::pair;
using std::vector;

// Node identifier in the range [0..N)
using NodeId = uint16_t;

// An index in the State::order array
//
// State::position and State::order are used to map NodeId <-> Position:
//
// node_id = state.order[position];
// position = state.position[node_id];
//
// I.e., state.position[node_id] returns the current position of node_id in the
// array State::order.
// Invariant: node_id == state.order[state.position[node_id]]
using Position = uint16_t;

// A move can be none, one or two node_ids to flip (if less than two, NO_MOVE
// will be in move.second or both fields of the move).
// NOTE: If adding and removing at the same time, the removal must be noted
// in ``move.first``.
using Move = pair<NodeId, NodeId>;
const uint16_t NO_MOVE = -1;

// Independent Set state representation
//
// A ``State`` is one specific configuration (i.e., set of nodes selected to
// currently in the independent set). Whether a specific node_id is in the set
// can be queried using the state.in_set[node_id] field.
//
// Additionally, we are also tracking additional statistics of the state which
// allow for quicker queries and updates during the simulation:
//
//   * ``state.adjacent[node_id]`` counts the number of neighboring nodes of
//     node_id which are in the set.
//
//   * ``state.size`` counts the number of nodes in the set
//
//   * ``state.vacant`` counts state.size + the number of vacant nodes (no
//     neighbors, called "free" in the paper, but that is a reserved word.)
//
//   * ``state.single`` counts state.vacant + the number of nodes with a single
//     neighbor
//
//   * ``state.order`` and ``state.position`` represent an ordering of all the
//     node_ids which satisfies:
//
//     position[node_id] < size \forall node_id : in_set[node_id] == true
//     position[node_id] < vacant \forall node_id : adjacent[node_id] == 0
//     position[node_id] < single \forall node_id : adjacent[node_id] == 1
//
//     node_id == order[position[node_id]]
//
class State {
public:
  // Create an zero size state (used in STL containers)
  State() {}

  // Create an empty state with N nodes
  //
  // This initializes all statistics for the empty state (no nodes in the set,
  // all adjacency counters are zero, and all nodes are in the "vacant" group).
  State(int N)
      : in_set(N), adjacent(N), order(N), position(N), size(0), vacant(N),
        single(N) {
    for (int i = 0; i < N; i++)
      order[i] = position[i] = i;
  }

  // Move the node with id `i` to position `target` in the order array
  //
  // This is achieved by swapping it with the node currently at the target
  // position.
  void reorder(NodeId i, Position target) {
    NodeId j = order[target];
    Position current = position[i];
    std::swap(order[current], order[target]);
    std::swap(position[i], position[j]);
  }

  // Add the node with id `i` to the set and update statistics.
  //
  // This method requires that the caller passes in a list of neighbors of the
  // node with id `i` (the state itself has no notion of graph connectivity).
  void add(NodeId i, const vector<NodeId> &neighbors) {
    // Update the in_set boolean variable
    assert(!in_set[i]);
    in_set[i] = true;

    // Update node ordering to move `i` into the in_set group.
    // This moves the node to position `size` and then increments `size`. As
    // a result, `i` then satisfies ``position[i] < size``.
    // NOTE: This will swap the node with another one that is currently at that
    // position (and, therefore, in the same group as `i`), keeping the
    // ordering invariants intact.
    reorder(i, size);
    size++;

    // Update node ordering to staisfy requirements for the neighbors.
    for (const NodeId &j : neighbors) {
      if (adjacent[j] == 0) {
        // If the neighbor is currently vacant, it will have one neigbor and
        // we need to move it from the `vacant` to the `single` group. This is
        // achieved by moving it to the end of the vacant section and then
        // decreasing the size of that section.
        // NOTE: Because `single` counts the those with zero and one neighbors
        // (as well as those in_set), we don't need to increase `single` at the
        // same time.
        reorder(j, vacant - 1);
        vacant--;
      } else if (adjacent[j] == 1) {
        // If the neighbor currently has one adjacent node in the set, it will
        // have two and we need to remove it from the `single` group. This is
        // achieved by moving it to the end and decreasing single.
        reorder(j, single - 1);
        single--;
      }
      // Actually update the adjacency count.
      adjacent[j]++;
    }
  }

  // Remove the node with id `i` from the set and update statistics.
  void remove(NodeId i, const vector<NodeId> &neighbors) {
    // Update the in_set boolean variable
    assert(in_set[i]);
    in_set[i] = false;

    // Update node ordering to move `i` out of the in_set group.
    // This moves the node to position `size-1` and then decrements `size`.
    reorder(i, size - 1);
    size--;

    // Update node ordering to satisfy requirements for the neighbors.
    for (const NodeId &j : neighbors) {
      if (adjacent[j] == 1) {
        // If the neighbor currently has one adjacencies, it will become free
        // and we need to move it to the `vacant` group. This is achieved by
        // moving it directly after the vacant section and then increasing the
        // size of that section.
        reorder(j, vacant);
        vacant++;
      } else if (adjacent[j] == 2) {
        // If the neighbor currently has two adjacencies, it will become single
        // and we need to move it to the `single` section. This is achieved by
        // moving it direclty after the single section and then increasing the
        // size of that section.
        reorder(j, single);
        single++;
      }
      // Actually decrease the adjacency counter.
      adjacent[j]--;
    }
  }

  // boolean variables indicating for each node_id whether it is in the set.
  vector<bool> in_set;
  // counter indicating the number of adjacent nodes in the set for each node.
  vector<NodeId> adjacent;
  // An ordering of the nodes which has contiguous sections for each type:
  // in_set, vacant, single and other.
  vector<NodeId> order;
  // The position of each node in the current odering.
  vector<Position> position;
  // The number of nodes currently in the set.
  int size;
  // size + the number of nodes currently without any neighbors in the set.
  int vacant;
  // vacant + the number of nodes with exactly one neighbor in the set.
  int single;
};
