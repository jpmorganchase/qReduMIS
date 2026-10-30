// SPDX-License-Identifier: Apache-2.0
// Copyright 2023: Amazon Web Services, Inc
#pragma once

#include <cstdint>
#include <random>

#include "pcg_random.hpp"

class Rng : public pcg32 {
 public:
  Rng() : pcg32() {}
  Rng(uint32_t seed) : pcg32(seed) {}

  static uint32_t generate_seed();

  inline uint32_t uint32() { return (*this)(); }

  inline double uniform() {
    static std::uniform_real_distribution<> uniform_dist(0.0, 1.0);
    return uniform_dist(*this);
  }
};
