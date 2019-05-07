# Binance has a huge number of pairs so I have decided to split its data into multiple repositories.
# At the time I'm writing this, I count 467 pairs, and each one has approximately 100Mo of data.
# So we have about 50Go of data.

EXCHANGE=binance
DELAY=250

pushd $CRYPTOBIGBRO_PATH_TO_DATA/$EXCHANGE
source $CRYPTOBIGBRO_PATH_TO_CODE/venv/bin/activate

instruments=`python $CRYPTOBIGBRO_PATH_TO_CODE/cryptobigbro.py list-instruments $EXCHANGE`

for i in ${instruments//,/ }
do
    x=$(cksum <<< $i | cut -f 1 -d ' ')
    idx=$(($x%16)) # between 0 and 15
    pushd $idx
    git pull
	python $CRYPTOBIGBRO_PATH_TO_CODE/cryptobigbro.py fetch-ohlcv $EXCHANGE . --instruments ${i} --delay ${DELAY}
    popd
done

for idx in {0..15}
do
    pushd $idx
    git add *
    git commit -a -m "Update OHLCV data."
    git push -u origin master
    popd
done

popd