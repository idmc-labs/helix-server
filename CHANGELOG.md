# Changelog

## [v2025.12.31-dev1](https://github.com/idmc-labs/helix-server/compare/v2025.12.31..v2025.12.31-dev1) - 2026-01-12
### Changes:

#### 🚀  Features

- *(ci)* Add commit lint - ([46e7f1a](https://github.com/idmc-labs/helix-server/commit/46e7f1a05c58d30ecab3883956a13419a92689de))

#### 🐛 Bug Fixes

- *(markuploaded)* Use s3 get_object to read file's first 4KB - ([f7e18d6](https://github.com/idmc-labs/helix-server/commit/f7e18d6a82fe61cc616356097a3d0e890a2c5d6f))

### 🍻 Pull Requests (1)
- (#702) [Fix(markuploaded): Reads a chunk of file to determine mimetype of the…](https://github.com/idmc-labs/helix-server/pull/702)


## [v2025.12.31](https://github.com/idmc-labs/helix-server/compare/sprint3.0.0..v2025.12.31) - 2026-01-08
### Changes:

#### 🚀  Features

- Build for linux/amd64 for docker tag/push script - ([783e18c](https://github.com/idmc-labs/helix-server/commit/783e18c2e22f162abcc3a36355dd990645eb79d8))
- Integrate with fugit - ([ffd3175](https://github.com/idmc-labs/helix-server/commit/ffd3175dc1cc63b29c27a471f15e0ff88d4ba1dd))
- Add support for helm snapshot - ([45acb74](https://github.com/idmc-labs/helix-server/commit/45acb749512ddda9dd68e9c06fedd73cb962ee69))

#### 🐛 Bug Fixes

- *(config)* Changes nginx proxy payload size limit to 5G - ([fa233c5](https://github.com/idmc-labs/helix-server/commit/fa233c587079117108eefa90cb8da77dbffebc4c))
- *(config)* Fix s3 endpoint url key - ([c6ea070](https://github.com/idmc-labs/helix-server/commit/c6ea0700092783f5829c0fe81cb7c495f7244e2b))
- *(copilot)* This commit merges the docker configs - ([09e145c](https://github.com/idmc-labs/helix-server/commit/09e145ce118b103e6964cb36d5b6434a59e03d5e))
- *(idus)* Add transaction atomic, clean logger msg for idus generation. - ([837643e](https://github.com/idmc-labs/helix-server/commit/837643e897c19552f23f847354c9e86daeda5ecb))
- *(idus_generation)* Handle failed idus generation - ([cb32679](https://github.com/idmc-labs/helix-server/commit/cb32679fd6a8ebd2d47607151add00fcc9a11cac))
- *(proxy-payload)* Adds proxy payload size in api service ([#694](https://github.com/idmc-labs/helix-server/issues/694)) - ([6643286](https://github.com/idmc-labs/helix-server/commit/66432865340b9081f1cba218e917468bede8569b))
- *(uv)* Python version constraint - ([268c3d7](https://github.com/idmc-labs/helix-server/commit/268c3d71c996a592052c383d19b4bac519fa1e11))
- Fixup! fix(config): fix s3 endpoint url key - ([bd17427](https://github.com/idmc-labs/helix-server/commit/bd17427d429150c69b40386bd8011a7c3d736a19))

#### ⚙️ Miscellaneous Tasks

- *(alpha-2)* Add test yaml file for alpha-2 as prod. - ([72a4d12](https://github.com/idmc-labs/helix-server/commit/72a4d1267b627732329ac8f16deea63186400164))
- *(client)* Add option to share source to particular clients. - ([da86fb3](https://github.com/idmc-labs/helix-server/commit/da86fb302b2453d7b6ace99eee8125849368eedd))
- *(external-api)* Hide source from query level, remove extra serializer to hide source - ([66f481c](https://github.com/idmc-labs/helix-server/commit/66f481cf814ad7f7d09a23dea6f59be8aaba60c5))
- *(external-api)* Only remove source_url, not source and source_type from external apis. - ([8154360](https://github.com/idmc-labs/helix-server/commit/81543601ef586dc224c061ecfcdaf1e89a9c036c))
- *(external-api)* Update test case for sharing sources in apis. - ([b1a8d6b](https://github.com/idmc-labs/helix-server/commit/b1a8d6bccfa39b682362ad4f0ac4b50753124036))
- *(external-api-dump)* Hide url link from standard_popup_text - ([81c2064](https://github.com/idmc-labs/helix-server/commit/81c206468af0f985faa671b11311ce01a9bf3486))
- *(external_api)* Remove sources info from gidd exports for client with no share permission. - ([c0fc8d2](https://github.com/idmc-labs/helix-server/commit/c0fc8d294db321199df1063e6ca7bdb7a36633a3))
- *(idus)* Dump separate file excluding source_url for idus data in ExternalApiDump table. - ([e9ed8ad](https://github.com/idmc-labs/helix-server/commit/e9ed8adac83ed0d89e9637e53c131937dd8864c1))
- *(postgres)* Upgrade postgres version - ([f908c88](https://github.com/idmc-labs/helix-server/commit/f908c883c22c412f42fb7c951dc0e9692f423c65))

### 🍻 Pull Requests (10)
- (#679) [Upgrade postgres version](https://github.com/idmc-labs/helix-server/pull/679)
- (#683) [Feat: add support for helm snapshot](https://github.com/idmc-labs/helix-server/pull/683)
- (#687) [SOURCE_INFO: Add option to share source to particular clients.](https://github.com/idmc-labs/helix-server/pull/687)
- (#689) [Feature/presigned url](https://github.com/idmc-labs/helix-server/pull/689)
- (#694) [Fix(proxy-payload): adds proxy payload size in api service](https://github.com/idmc-labs/helix-server/pull/694)
- (#697) [Project: Dec sprint](https://github.com/idmc-labs/helix-server/pull/697)
- (#698) [Fix(config): fix s3 endpoint url key](https://github.com/idmc-labs/helix-server/pull/698)
- (#699) [Fix(idus): add transaction atomic, clean logger msg for idus generation.](https://github.com/idmc-labs/helix-server/pull/699)
- (#700) [Fix(idus_generation): handle failed idus generation](https://github.com/idmc-labs/helix-server/pull/700)
- (#701) [Fix(copilot): This commit merges the docker configs](https://github.com/idmc-labs/helix-server/pull/701)

### :tada: New Contributors (1)

- [@ln2khanal](https://github.com/ln2khanal) made their first contribution

## [sprint3.0.0](https://github.com/idmc-labs/helix-server/compare/sprint4.0.3..sprint3.0.0) - 2025-05-30
### Changes:

#### 🚀  Features

- *(config)* Setup pre-commit - ([f898a8f](https://github.com/idmc-labs/helix-server/commit/f898a8fc195053d48ba29004c1c614ec5e26c1b2))
- *(deps)* Replace poetry with uv - ([ad60fb7](https://github.com/idmc-labs/helix-server/commit/ad60fb7901197a8d1298f7e2df411bd2dc95ce15))
- *(docker)* Update Dockerfile with multi-stage builds - ([e16e6f1](https://github.com/idmc-labs/helix-server/commit/e16e6f17401f3995c473f169fb165356aa9b929b))

#### 🐛 Bug Fixes

- *(deps)* Remove poetry lock - ([9cf93fc](https://github.com/idmc-labs/helix-server/commit/9cf93fc4550c3ce095f92a88aa9733317e2b7897))
- *(event/figure)* Migrate event/figure dates migration to command script - ([a4aee8b](https://github.com/idmc-labs/helix-server/commit/a4aee8b7cf0cbbbc41b96e64ec1d9e915b423e97))
- *(gh)* Fix new line issue - ([f115d5f](https://github.com/idmc-labs/helix-server/commit/f115d5f39612e69781c4b32cbd910d70691eb0cd))
- *(lint)* Fix check-docstring-first - ([964245e](https://github.com/idmc-labs/helix-server/commit/964245e69ae46254be8ffaf1210ea2625a0db951))
- *(lint)* Fix check-builtin-literals - ([ac85ba4](https://github.com/idmc-labs/helix-server/commit/ac85ba414e3caed75e924b77a56fd083e304c162))
- *(lint)* Fix name-tests-test issue - ([b5d9ae8](https://github.com/idmc-labs/helix-server/commit/b5d9ae8d34def35de50839a311ebaacacdf4257a))
- *(tests)* Fix fail test - ([49351d3](https://github.com/idmc-labs/helix-server/commit/49351d375923519f85a642294941bba7172843ee))

#### 🚜 Refactor

- *(entry)* Add bulkmgr and Update migration script for source file - ([4076cc2](https://github.com/idmc-labs/helix-server/commit/4076cc239885ad154ac4ac896ca5f91a7545cdb1))

#### ⚙️ Miscellaneous Tasks

- *(Ahhs)* Refactor ahhs command - ([8c21b90](https://github.com/idmc-labs/helix-server/commit/8c21b90d55b54240881239bea8865c67c6499f43))
- *(buildspec)* Enable DOCKER_BUILDKIT - ([e3a4ac3](https://github.com/idmc-labs/helix-server/commit/e3a4ac3f5cec2aa3ff91211405fa246393be6e10))
- *(gh)* Update workflow and job name - ([1e35d53](https://github.com/idmc-labs/helix-server/commit/1e35d53659af3670bcef7cfd4aed572edabac427))
- *(graphql)* Update schema.graphql - ([28b3a04](https://github.com/idmc-labs/helix-server/commit/28b3a04d8ffa798c602b95949f7bff3b6eff72d2))
- *(pre-commit)* Precommit autofix - ([82d0575](https://github.com/idmc-labs/helix-server/commit/82d0575314eb957cdd496300bf93d157dd329168))

### 🍻 Pull Requests (1)
- (#664) [Project / Sprint 3.1](https://github.com/idmc-labs/helix-server/pull/664)


<!-- generated by git-cliff -->
