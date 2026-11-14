#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
"${MAVEN:-mvn}" -f pom.xml clean package dependency:tree -Dscope=runtime -DoutputFile=target/runtime-dependencies.txt
"${MAVEN:-mvn}" -f spring-jpa/pom.xml clean package dependency:tree -Dscope=runtime -DoutputFile=target/runtime-dependencies.txt
java -Djarmode=tools -jar spring-jpa/target/stars-0.0.1-SNAPSHOT.jar extract --destination spring-jpa/target/extracted
