# Cedar Integration Tests

This repository contains integration tests for the Cedar policy language. It is a mixture of handwritten tests and auto-generated tests produced using our fuzzing infrastructure in [cedar-spec](https://github.com/cedar-policy/cedar-spec). If you are developing an implementation of Cedar, please consider using these tests to check your work!

## Directory structure

* `tests/`: Handwritten integration tests
* `sample-data/`: Entities and schemas used by the handwritten tests
* `corpus-tests.tar.gz`: Auto-generated tests
* `cedar/`: Submodule pointing to the version of [cedar](https://github.com/cedar-policy/cedar) used to to generate the most recent corpus tests
* `cedar-spec/`: Submodule pointing to the version of [cedar-spec](https://github.com/cedar-policy/cedar-spec) used to to generate the most recent corpus tests

## Test format

An integration test is a JSON file with the following fields:

* `policies`: The name of the Cedar policy file (`*.cedar`)
* `entities`: The name of the entities file (`*.entities.json`)
* `schema`: The name of the Cedar schema file (`*.cedarschema`)
* `shouldValidate`: Whether the policy validate using the schema (true/false)
* `requests`: Sequence of authorization requests and expected results (see below)

Each request has the following fields:

* `description`: Description for the request
* `principal`: Principal for the request (optional)
* `action`: Action for the request (optional)
* `resource`: Resource for the request (optional)
* `context`: Context for the request
* `validateRequest`: Whether to enable request validation (true/false)
* `decision`: Expected decision (Allow/Deny)
* `reason`: Expected policies that led to the decision
* `errors`: Expected policies that resulted in errors

## How should you use these tests?

We recommend using these tests in your CI to gate commits. For example, we use these tests in GitHub Actions for our [cedar](https://github.com/cedar-policy/cedar) and [cedar-java](https://github.com/cedar-policy/cedar-java) repositories.

## How are the corpus tests generated?

The corpus tests are generated over a 6 hour run of the [`abac` target](https://github.com/cedar-policy/cedar-spec/blob/main/cedar-drt/fuzz/fuzz_targets/abac.rs). This target uses coverage-guided fuzzing, which will choose to save an input to the "corpus" if it generates new coverage compared to previous inputs. Before uploading the corpus, we run [`cmin`](https://manpages.ubuntu.com/manpages/bionic/man1/afl-cmin.1.html) to reduce the corpus size.

## What do the auto-generated tests look like?

The `scripts/` folder includes a script for inspecting the auto-generated corpus tests. It can be used to print statistics about a single corpus, or to compare two corpuses:

```shell
# get a summary for corpus-tests.tar.gz
python3 scripts/get_corpus_stats.py corpus-tests.tar.gz
# compare corpus-tests.tar.gz against a previous corpus corpus-tests-old.tar.gz
python3 scripts/get_corpus_stats.py corpus-tests.tar.gz --original corpus-tests-old.tar.gz
```

This script is run as part of CI. You can find the output in the GitHub Actions tab under the "Print corpus statistics" job.

## Security

See [CONTRIBUTING](CONTRIBUTING.md#security-issue-notifications) for more information.

## License

This project is licensed under the Apache-2.0 License.
