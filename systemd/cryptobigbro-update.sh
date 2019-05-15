EXCHANGE=$1
DELAY=$2
GITHUB_TOKEN=$3
cd $CRYPTOBIGBRO_PATH_TO_DATA
git pull # pull existing data
source $CRYPTOBIGBRO_PATH_TO_CODE/venv/bin/activate
instruments=`python $CRYPTOBIGBRO_PATH_TO_CODE/cryptobigbro.py list-instruments $EXCHANGE`
for i in ${instruments//,/ }
do
    REPONAME=$EXCHANGE-$i
    if [ ! -d "$REPONAME" ]; then 
        python $CRYPTOBIGBRO_PATH_TO_CODE/systemd/create-github-repository.py $GITHUB_TOKEN $REPONAME
        mkdir $REPONAME
        pushd $REPONAME
        git init
        git remote add origin git@github.com:cryptobigbro/$REPONAME.git
        python $CRYPTOBIGBRO_PATH_TO_CODE/cryptobigbro.py instrument-info $EXCHANGE $i > info.json
        git add *
        git commit -a -m "Initial commit with info.json."
        git push -u origin master
        popd
    fi
    pushd $REPONAME
	python $CRYPTOBIGBRO_PATH_TO_CODE/cryptobigbro.py fetch-ohlcv $EXCHANGE . --instruments ${i} --delay ${DELAY}
    git add *
    git commit -a -m "Update OHLCV data."
    git push -u origin master
    popd
done