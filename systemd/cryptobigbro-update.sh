EXCHANGE=$1
DELAY=$2
TIMEFRAMES=$3

source $CRYPTOBIGBRO_PATH_TO_CODE/venv/bin/activate

pushd $CRYPTOBIGBRO_PATH_TO_DATA

instruments=`python $CRYPTOBIGBRO_PATH_TO_CODE/cryptobigbro.py list-instruments $EXCHANGE`

for i in ${instruments//,/ }
do
    REPONAME=$EXCHANGE-$i
    if [ ! -d "$REPONAME" ]; then 
        python $CRYPTOBIGBRO_PATH_TO_CODE/systemd/create-github-repository.py $CRYPTOBIGBRO_GITHUB_TOKEN $REPONAME
        mkdir $REPONAME
        pushd $REPONAME
        git init
        git remote add origin git@github.com:cryptobigbro/$REPONAME.git
        python $CRYPTOBIGBRO_PATH_TO_CODE/cryptobigbro.py instrument-info $EXCHANGE $i > info.json
        git add *
        git commit -a -m "Initial commit with info.json."
        git push -u origin master
        popd

        # For coinbasepro and bitmex copy previously fetched data #todo remove this later
        for t in ${TIMEFRAMES//,/ }
        do
            if [ -f $CRYPTOBIGBRO_PATH_TO_DATA/$EXCHANGE/$EXCHANGE-$i-$t.csv ]; then
                cp $CRYPTOBIGBRO_PATH_TO_DATA/$EXCHANGE/$EXCHANGE-$i-$t.csv $REPONAME
                pushd $REPONAME
                git add *
                git commit -a -m "Add previously fetched data."
                git push -u origin master
                popd
            fi
        done
    fi
    pushd $REPONAME
    git pull
	python $CRYPTOBIGBRO_PATH_TO_CODE/cryptobigbro.py fetch-ohlcv $EXCHANGE . --instruments ${i} --delay ${DELAY} --timeframes ${TIMEFRAMES}
    git add *
    git commit -a -m "Update OHLCV data."
    git push -u origin master
    popd
done

popd