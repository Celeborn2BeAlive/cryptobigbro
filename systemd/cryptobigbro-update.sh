EXCHANGE=$1
cd $CRYPTOBIGBRO_PATH_TO_DATA/$EXCHANGE
git pull # pull existing data
source $CRYPTOBIGBRO_PATH_TO_CODE/venv/bin/activate
instruments=`python $CRYPTOBIGBRO_PATH_TO_CODE/cryptobigbro.py list-instruments $EXCHANGE`
for i in ${instruments//,/ }
do
	python $CRYPTOBIGBRO_PATH_TO_CODE/cryptobigbro.py fetch-ohlcv $EXCHANGE . --instruments ${i}
	git add *
	git commit -a -m "Update OHLCV data for exchange ${EXCHANGE} and instrument ${i}"
done
git push -u origin master
