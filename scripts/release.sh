#!/usr/bin/env bash
set -e; set -o pipefail
cd "${BASH_SOURCE%/*}/" || exit

cd ../../country-levels-export

cp ../country-levels/docs/export_readme.md README.md
echo '{"name": "country-levels","version": "1.0.0"}' > package.json

rm -rf release

for i in 5 7 8
do
  mkdir -p release/q$i/geojson
  cp *.json release/q$i
  cp *.md release/q$i
  cp -R geojson/q$i/. release/q$i/geojson
  cd release/q$i || exit
  tar -czvf ../export_q$i.tgz .
  cd ../..
  rm -rf release/q$i
done
