<!-- markdownlint-disable -->
# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-03-24

The highlight of this changes is that config files are now TOML instead of JSON. The old JSON examples are gone, the schema is stricter, and the simulator now has a much nicer foundation for real-world setups like multiple clients, lifecycle messages, richer schedules, and inline payload generators.

### <!-- 0 -->Features
- Switch commands and examples to the TOML  ([79fdee6](https://github.com/marcelo-6/mqtt-sim/commit/79fdee6c572bc1921deb6c428feed207015af61d))

- Add session scheduling and lifecycle publishing  ([b1c2e65](https://github.com/marcelo-6/mqtt-sim/commit/b1c2e6517a92fa3fe5b58c9944da2f038d3d7a75))

- Add inline payload builders and generator  ([88d8053](https://github.com/marcelo-6/mqtt-sim/commit/88d8053d7a0172c5cd7292e61fe587f75adecb8a))

- Resolve toml expansion, and client sessions  ([40fc86c](https://github.com/marcelo-6/mqtt-sim/commit/40fc86c6ab7a5e7f251a2ea8ee8fe5dbced14533))

- Add TOML schema models and loader  ([618dc86](https://github.com/marcelo-6/mqtt-sim/commit/618dc86cb02b64543d7c2d185abeda3be49b591c))


### <!-- 1 -->Bug Fixes
- Make the live table topic column size more predictable  ([4a418a3](https://github.com/marcelo-6/mqtt-sim/commit/4a418a38253b3480b4a8d4c15fb9057e2d0df65e))


### <!-- 3 -->Documentation
- Rewrite public docs for the TOML schema  ([72d939e](https://github.com/marcelo-6/mqtt-sim/commit/72d939e4725ca9d4c39595dadb0967d50f129389))

- Update README badges  by @marcelo-6 ([a94f914](https://github.com/marcelo-6/mqtt-sim/commit/a94f914e7f551e340f621609a03a021f4d9a78d1))


### <!-- 6 -->Testing
- Set coverage threshold to 65  ([bb271d2](https://github.com/marcelo-6/mqtt-sim/commit/bb271d27de0929f065ccf52b8151e756c09bfa08))


### <!-- 7 -->Miscellaneous Tasks
- Update the development status classifier to Production/Stable  ([3e3c394](https://github.com/marcelo-6/mqtt-sim/commit/3e3c394dce7524e1358c2e2e2c3513e3eca749b5))

- Bump docker/setup-buildx-action from 3 to 4  by @dependabot[bot] in [#26](https://github.com/marcelo-6/mqtt-sim/pull/26) ([5881202](https://github.com/marcelo-6/mqtt-sim/commit/5881202e3ba91a313fa1d5d7cfc1ff62f37d30bf))

- Bump docker/metadata-action from 5 to 6  by @dependabot[bot] in [#25](https://github.com/marcelo-6/mqtt-sim/pull/25) ([baeec14](https://github.com/marcelo-6/mqtt-sim/commit/baeec14327548cfd8acf2e54c6084ec6f87d6173))

- Bump docker/login-action from 3 to 4  by @dependabot[bot] in [#27](https://github.com/marcelo-6/mqtt-sim/pull/27) ([f94dc4b](https://github.com/marcelo-6/mqtt-sim/commit/f94dc4b9d7ed7451ab6a6a730433a5df9bba4994))

- Bump docker/build-push-action from 6 to 7  by @dependabot[bot] in [#28](https://github.com/marcelo-6/mqtt-sim/pull/28) ([1dd97cb](https://github.com/marcelo-6/mqtt-sim/commit/1dd97cb6cf4b5d02f3fded3fcfa9a82c61c79810))


### New Contributors
* @dependabot[bot] made their first contribution in [#26](https://github.com/marcelo-6/mqtt-sim/pull/26)

## [0.0.1] - 2026-02-25

### <!-- 0 -->Features
- Add package/docker publish workflows and tag-driven release workflow  by @marcelo-6 ([6d7c41d](https://github.com/marcelo-6/mqtt-sim/commit/6d7c41d7895b12174ad2c6ec9b13dd58486c7646))

- Add changelog tooling, release helper, and release notes extractor  by @marcelo-6 ([63aa28e](https://github.com/marcelo-6/mqtt-sim/commit/63aa28efaa4c1c672929fa60ec79cc8e893681af))

- Add compose with local mosquitto broker  by @marcelo-6 ([d9969a5](https://github.com/marcelo-6/mqtt-sim/commit/d9969a5735390efbaea8bcb3d980973c2ea904d3))

- Add colorful table render  by @marcelo-6 ([00b3f18](https://github.com/marcelo-6/mqtt-sim/commit/00b3f189e93f816a8eb4b4da3632aef0b17163e6))

- Add common exception handling and logging  by @marcelo-6 ([f932788](https://github.com/marcelo-6/mqtt-sim/commit/f932788911752e13c3cf554a4067c64ce5205832))

- Add run and validate commands with rich table/log output modes  by @marcelo-6 ([8acdb2f](https://github.com/marcelo-6/mqtt-sim/commit/8acdb2fbb936d7cc0c58b3f163c21e51e396b164))

- Add asyncio scheduler engine and MQTT adapter  by @marcelo-6 ([4ff6c68](https://github.com/marcelo-6/mqtt-sim/commit/4ff6c68a7bcfe1ad3b5bf48f8e38c453e25293e4))

- Add payload generators and builders  by @marcelo-6 ([209ce94](https://github.com/marcelo-6/mqtt-sim/commit/209ce94b61a576f53fb60c700e512f0fea3f0917))

- Add new simulator config schema  by @marcelo-6 ([f9dd64a](https://github.com/marcelo-6/mqtt-sim/commit/f9dd64a5e98c950cc2f7c785ab7bbe6ca2331741))

- Add package with Typer version command  by @marcelo-6 ([c65a1fa](https://github.com/marcelo-6/mqtt-sim/commit/c65a1fae3b3ac19f62fa832c1a712f5b1ecbb66a))

- Update dockerfile to use python 3.12  by @vordimous ([81f7748](https://github.com/marcelo-6/mqtt-sim/commit/81f77487d6971d5c58b0b62a69e9004729a60c90))

- Add a build job to push the container image to the repo registry  by @vordimous ([b6eeae4](https://github.com/marcelo-6/mqtt-sim/commit/b6eeae428a75507557237decc4dc5cb6a18cc23a))


### <!-- 1 -->Bug Fixes
- Correct int generator type handling  by @marcelo-6 ([b55249a](https://github.com/marcelo-6/mqtt-sim/commit/b55249ae5b1b2b9d05be941894364e61004b7ac6))


### <!-- 2 -->Refactor
- Remove previous mqtt-simulator runtime tree  by @marcelo-6 ([e385688](https://github.com/marcelo-6/mqtt-sim/commit/e3856886d9180bb596d69ecdb14068b594da6d49))


### <!-- 3 -->Documentation
- Add release guide  by @marcelo-6 ([e91fefc](https://github.com/marcelo-6/mqtt-sim/commit/e91fefc3bf886b4e424649f057ca2b448aee5016))

- Format readme and add mqttui gif  by @marcelo-6 in [#16](https://github.com/marcelo-6/mqtt-sim/pull/16) ([97098e0](https://github.com/marcelo-6/mqtt-sim/commit/97098e0305d773dfb70d27fb3b72ae525cd0f709))

- Add extensive examples to documentation  by @marcelo-6 ([57e9622](https://github.com/marcelo-6/mqtt-sim/commit/57e962255a6382a174eb77d150b4a19b360bd966))

- Add colorful table render gif  by @marcelo-6 ([8135b9c](https://github.com/marcelo-6/mqtt-sim/commit/8135b9c1d603a94b08ea5036c583f2fb8b815f2b))

- Update README, Dockerfile, requirements, and config docs  by @marcelo-6 ([26e136e](https://github.com/marcelo-6/mqtt-sim/commit/26e136e1a8bdd38e55f63bc1f8b815bcaa3533e5))

- Added license  by @marcelo-6 ([d31864e](https://github.com/marcelo-6/mqtt-sim/commit/d31864eb7f06e26e4b2a064774aca865db59e99e))


### <!-- 5 -->Styling
- Lint of table render changes  by @marcelo-6 ([4c1bbe5](https://github.com/marcelo-6/mqtt-sim/commit/4c1bbe5575d3480fb70888a75fc85aaf5349c7f7))

- Lint in pytests  by @marcelo-6 ([6b7f86e](https://github.com/marcelo-6/mqtt-sim/commit/6b7f86e37534d778528819066d3d0fde17c445bb))


### <!-- 6 -->Testing
- Add changelog extraction tests  by @marcelo-6 ([890007d](https://github.com/marcelo-6/mqtt-sim/commit/890007dc67b9d1859636d1b9a923917048de38cb))

- Updated coverage to 70%  by @marcelo-6 ([bf9b6e1](https://github.com/marcelo-6/mqtt-sim/commit/bf9b6e11e6f20f7b98f8ca9aad0f0b6005c8d218))

- CLI/runtime/payload/logging coverage  by @marcelo-6 ([dc3a7a0](https://github.com/marcelo-6/mqtt-sim/commit/dc3a7a0e57ef7617ba83cbdf1035bc5a3aacb2ce))

- Lower test coverage gate for now  by @marcelo-6 ([f0dcb1a](https://github.com/marcelo-6/mqtt-sim/commit/f0dcb1afbac1d0ef07a5ff163d453fa074082262))

- Add pytest for cli and regression coverage  by @marcelo-6 ([526022b](https://github.com/marcelo-6/mqtt-sim/commit/526022b7ee524e2c30d412efe9185c18688e46a9))


### <!-- 7 -->Miscellaneous Tasks
- Prepare v0.0.1  by @marcelo-6 in [#17](https://github.com/marcelo-6/mqtt-sim/pull/17) ([e515e23](https://github.com/marcelo-6/mqtt-sim/commit/e515e2358aff8d95309d071778d83a9ceb77f6a8))

- Updated packaging script for local test of cd pipeline  by @marcelo-6 ([2fc31e5](https://github.com/marcelo-6/mqtt-sim/commit/2fc31e57f47c09266d337afaab7024b28468430c))

- Added github template cliff  by @marcelo-6 ([cb80338](https://github.com/marcelo-6/mqtt-sim/commit/cb8033809da1fff3de29e9909d144af382494dd8))

- Add documented CI/CD parity and release recipes  by @marcelo-6 ([4a8dbc8](https://github.com/marcelo-6/mqtt-sim/commit/4a8dbc869db4370168041141e5dd585717d19094))

- Add script to generate gifs of example config files for docs  by @marcelo-6 ([549b216](https://github.com/marcelo-6/mqtt-sim/commit/549b2169205505cb93dd049a602982351c821f92))

- Add new implementation example configs and sample pickle payload  by @marcelo-6 ([a2ae843](https://github.com/marcelo-6/mqtt-sim/commit/a2ae8436ffd9eaf963d701940b50bb117dffc736))

- Add cache install of just  by @marcelo-6 in [#9](https://github.com/marcelo-6/mqtt-sim/pull/9) ([d4c08cb](https://github.com/marcelo-6/mqtt-sim/commit/d4c08cbf8ea49ceccd86b60b754568ab81cbda3d))

- Updated dependencies version  by @marcelo-6 ([e0a6b36](https://github.com/marcelo-6/mqtt-sim/commit/e0a6b36cb0b711dcb1e63afa401216e6aec2c126))

- Add justfile, tooling config, tests, and CI  by @marcelo-6 ([4c4c766](https://github.com/marcelo-6/mqtt-sim/commit/4c4c7668da3dcf754931ff879b96a3cf5e15a942))

- Ignore secrets folder  by @marcelo-6 ([d543b19](https://github.com/marcelo-6/mqtt-sim/commit/d543b1964f1ff6b6abe27fe557f984fc39ad212d))


### Other
- Migrate to pdm-backend and add PyPI metadata  by @marcelo-6 ([75c5e53](https://github.com/marcelo-6/mqtt-sim/commit/75c5e538e89916845418a08ae145ab2886f6da60))


### New Contributors
* @marcelo-6 made their first contribution in [#17](https://github.com/marcelo-6/mqtt-sim/pull/17)
* @DamascenoRafael made their first contribution
* @vordimous made their first contribution
* @raph-topo made their first contribution
* @Maasouza made their first contribution

