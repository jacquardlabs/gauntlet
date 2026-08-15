# CHANGELOG

<!-- version list -->

## v0.13.1 (2026-08-15)

### Bug Fixes

- State the omit case in every judge's `anchor` placeholder
  ([#74](https://github.com/jacquardlabs/gauntlet/pull/74),
  [`1a890b4`](https://github.com/jacquardlabs/gauntlet/commit/1a890b485331b90597b3aefbea0a7ce9f4cddeac))

- Teach every judge the omit-not-null rule for all optional fields
  ([#74](https://github.com/jacquardlabs/gauntlet/pull/74),
  [`1a890b4`](https://github.com/jacquardlabs/gauntlet/commit/1a890b485331b90597b3aefbea0a7ce9f4cddeac))


## v0.13.0 (2026-08-09)

### Features

- Give the fleet correctness, simplicity, and language dimensions
  ([#71](https://github.com/jacquardlabs/gauntlet/pull/71),
  [`e7248dd`](https://github.com/jacquardlabs/gauntlet/commit/e7248dd5e1ece6ac7aceea01867c63b88d2d3761))


## v0.12.0 (2026-08-07)

### Documentation

- Point the README at the renamed ingest-notes section
  ([#70](https://github.com/jacquardlabs/gauntlet/pull/70),
  [`8a4a530`](https://github.com/jacquardlabs/gauntlet/commit/8a4a5308fa2ae84163898e37d192e3789feaf68b))

### Features

- Make every ingest accommodation visible in the report
  ([#70](https://github.com/jacquardlabs/gauntlet/pull/70),
  [`8a4a530`](https://github.com/jacquardlabs/gauntlet/commit/8a4a5308fa2ae84163898e37d192e3789feaf68b))


## v0.11.0 (2026-08-07)

### Bug Fixes

- Pass --root on a posture run, so §2 matches §1's worktree rule
  ([#66](https://github.com/jacquardlabs/gauntlet/pull/66),
  [`89a124d`](https://github.com/jacquardlabs/gauntlet/commit/89a124d2a30fd8ab46b0d074c9071bf763ce213b))

- Pass --root on every dispatch call §1 builds a worktree for
  ([#66](https://github.com/jacquardlabs/gauntlet/pull/66),
  [`89a124d`](https://github.com/jacquardlabs/gauntlet/commit/89a124d2a30fd8ab46b0d074c9071bf763ce213b))

### Features

- Give the repository artifact a branch in the review command
  ([#66](https://github.com/jacquardlabs/gauntlet/pull/66),
  [`89a124d`](https://github.com/jacquardlabs/gauntlet/commit/89a124d2a30fd8ab46b0d074c9071bf763ce213b))


## v0.10.5 (2026-08-07)

### Bug Fixes

- Fail closed when a judge's tools declaration cannot be read
  ([#63](https://github.com/jacquardlabs/gauntlet/pull/63),
  [`b562212`](https://github.com/jacquardlabs/gauntlet/commit/b562212993cf8b25e489283c758d023febebb711))

- Match the frontmatter delimiters on CRLF files
  ([#63](https://github.com/jacquardlabs/gauntlet/pull/63),
  [`b562212`](https://github.com/jacquardlabs/gauntlet/commit/b562212993cf8b25e489283c758d023febebb711))

- Read block-sequence tools: frontmatter in the independence check
  ([#63](https://github.com/jacquardlabs/gauntlet/pull/63),
  [`b562212`](https://github.com/jacquardlabs/gauntlet/commit/b562212993cf8b25e489283c758d023febebb711))


## v0.10.4 (2026-08-07)

### Bug Fixes

- Reconcile the document-anchor rule with the lanes subject to it
  ([#64](https://github.com/jacquardlabs/gauntlet/pull/64),
  [`fa282d3`](https://github.com/jacquardlabs/gauntlet/commit/fa282d39050881d4cb519f2efec7de8e3c3e5db8))


## v0.10.3 (2026-08-07)

### Bug Fixes

- Tell every judge to omit locus.line when a finding is not at one line
  ([#56](https://github.com/jacquardlabs/gauntlet/pull/56),
  [`9800148`](https://github.com/jacquardlabs/gauntlet/commit/9800148a407be18de0d217ce7127ee63f8aefbd1))


## v0.10.2 (2026-08-07)

### Bug Fixes

- Read the docs against themselves, and rule placement out of the lane
  ([#55](https://github.com/jacquardlabs/gauntlet/pull/55),
  [`f438dba`](https://github.com/jacquardlabs/gauntlet/commit/f438dba42dfd99c9d7fcf0f36fabac5d1eb0071b))

### Documentation

- Put all three artifacts in Use, and drop the stale install caveat
  ([#53](https://github.com/jacquardlabs/gauntlet/pull/53),
  [`13576ca`](https://github.com/jacquardlabs/gauntlet/commit/13576ca3173f43b273ff5979f65e33643bcd37be))

- Rule tracker maintenance out of scope ([#51](https://github.com/jacquardlabs/gauntlet/pull/51),
  [`6131fb7`](https://github.com/jacquardlabs/gauntlet/commit/6131fb712fe8d29673dfdfc1db7ed744bb510f64))


## v0.10.1 (2026-08-07)

### Bug Fixes

- State the trade-study seam on both sides ([#50](https://github.com/jacquardlabs/gauntlet/pull/50),
  [`5a8f524`](https://github.com/jacquardlabs/gauntlet/commit/5a8f5248957d52de8fd7127f69d9ca396e2a2de9))


## v0.10.0 (2026-08-07)

### Features

- Add the trade-study lane, the second bespoke document judge
  ([#49](https://github.com/jacquardlabs/gauntlet/pull/49),
  [`7b6d4ae`](https://github.com/jacquardlabs/gauntlet/commit/7b6d4aee9a42b416fa4e7bfdb9b6d877478a3373))


## v0.9.0 (2026-08-07)

### Features

- Add the falsifiability lane, the first document judge
  ([#48](https://github.com/jacquardlabs/gauntlet/pull/48),
  [`714cb05`](https://github.com/jacquardlabs/gauntlet/commit/714cb05fe969b6209fe2878a7dd359e4ad392b53))


## v0.8.0 (2026-08-07)

### Bug Fixes

- Let --document carry --root — every artifact kind shares that scope
  ([#47](https://github.com/jacquardlabs/gauntlet/pull/47),
  [`0ac9bfc`](https://github.com/jacquardlabs/gauntlet/commit/0ac9bfcde38caf2d7e9631a95654991064c96f37))

### Features

- Dispatch document artifacts at intake ([#47](https://github.com/jacquardlabs/gauntlet/pull/47),
  [`0ac9bfc`](https://github.com/jacquardlabs/gauntlet/commit/0ac9bfcde38caf2d7e9631a95654991064c96f37))


## v0.7.0 (2026-08-07)

### Bug Fixes

- Declare and type-check root on document artifacts
  ([#46](https://github.com/jacquardlabs/gauntlet/pull/46),
  [`417e4c1`](https://github.com/jacquardlabs/gauntlet/commit/417e4c1321b6e1cd3833dfa33ab6acdd7d6132de))

### Documentation

- Rule the document surface — one falsifiability lane, standards as data
  ([#45](https://github.com/jacquardlabs/gauntlet/pull/45),
  [`7a6bfd4`](https://github.com/jacquardlabs/gauntlet/commit/7a6bfd415f46cc20ab54274a8ea0c0853118e77d))

### Features

- Quote-match document anchors at ingest ([#46](https://github.com/jacquardlabs/gauntlet/pull/46),
  [`417e4c1`](https://github.com/jacquardlabs/gauntlet/commit/417e4c1321b6e1cd3833dfa33ab6acdd7d6132de))


## v0.6.0 (2026-08-07)

### Features

- Migrate the product and interface posture lanes
  ([#42](https://github.com/jacquardlabs/gauntlet/pull/42),
  [`7aeea44`](https://github.com/jacquardlabs/gauntlet/commit/7aeea44d97af4700a996904ef4916b2429ef584a))


## v0.5.0 (2026-08-07)

### Features

- Migrate the prompt and documentation posture lanes
  ([#41](https://github.com/jacquardlabs/gauntlet/pull/41),
  [`c246aa7`](https://github.com/jacquardlabs/gauntlet/commit/c246aa73f782d702ebf9c76348f7ecbd938c3f9f))


## v0.4.0 (2026-08-06)

### Features

- Migrate the first three posture lanes ([#40](https://github.com/jacquardlabs/gauntlet/pull/40),
  [`5ebd56e`](https://github.com/jacquardlabs/gauntlet/commit/5ebd56ebfd93c938a85e7432434a8fbd56ac3360))


## v0.3.0 (2026-08-06)

### Features

- Add the repository artifact kind and the posture mount
  ([#38](https://github.com/jacquardlabs/gauntlet/pull/38),
  [`6714d55`](https://github.com/jacquardlabs/gauntlet/commit/6714d5545e49f51ede85f8ca8a887892fd26c971))


## v0.2.0 (2026-08-06)

### Bug Fixes

- Three defects the new prompt lane found in its own changeset
  ([#35](https://github.com/jacquardlabs/gauntlet/pull/35),
  [`6c06b97`](https://github.com/jacquardlabs/gauntlet/commit/6c06b97b5815498cdaa0a4683fb1bd37cbf705c7))

### Features

- Migrate the product, pre-mortem, and prompt lanes
  ([#35](https://github.com/jacquardlabs/gauntlet/pull/35),
  [`6c06b97`](https://github.com/jacquardlabs/gauntlet/commit/6c06b97b5815498cdaa0a4683fb1bd37cbf705c7))

- Publish the pre-mortem register format, and dispatch only when its input exists
  ([#35](https://github.com/jacquardlabs/gauntlet/pull/35),
  [`6c06b97`](https://github.com/jacquardlabs/gauntlet/commit/6c06b97b5815498cdaa0a4683fb1bd37cbf705c7))


## v0.1.4 (2026-08-05)

### Bug Fixes

- Cap the recommendation, the one field with no stated limit
  ([#34](https://github.com/jacquardlabs/gauntlet/pull/34),
  [`0d88e00`](https://github.com/jacquardlabs/gauntlet/commit/0d88e0078fd92972777c2f74554957fa36fea4c0))


## v0.1.3 (2026-08-05)

### Bug Fixes

- Render a comment for the margin, not a report in it
  ([#33](https://github.com/jacquardlabs/gauntlet/pull/33),
  [`7b6bcd4`](https://github.com/jacquardlabs/gauntlet/commit/7b6bcd4824da71262fb29d1d65ee69d04be8bd6b))


## v0.1.2 (2026-08-05)

### Bug Fixes

- Stop posting the same defect twice, and keep track out of the diff
  ([#31](https://github.com/jacquardlabs/gauntlet/pull/31),
  [`7ebf8b3`](https://github.com/jacquardlabs/gauntlet/commit/7ebf8b3f02df694d82f3f0565425635bed6c507c))


## v0.1.1 (2026-08-05)

### Bug Fixes

- Split anchorable findings from the rest, and read a PR from a worktree
  ([#28](https://github.com/jacquardlabs/gauntlet/pull/28),
  [`6794c81`](https://github.com/jacquardlabs/gauntlet/commit/6794c81a59e60dcbf83b9e4871539bb2c0f764e2))


## v0.1.0 (2026-08-05)

- Initial Release

## v1.0.0 (2026-08-05)

- Initial Release
