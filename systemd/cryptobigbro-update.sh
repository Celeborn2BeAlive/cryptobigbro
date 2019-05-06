EXCHANGE=$1
DELAY=$2
cd $CRYPTOBIGBRO_PATH_TO_DATA/$EXCHANGE
git pull # pull existing data
source $CRYPTOBIGBRO_PATH_TO_CODE/venv/bin/activate
instruments=`python $CRYPTOBIGBRO_PATH_TO_CODE/cryptobigbro.py list-instruments $EXCHANGE`
for i in ${instruments//,/ }
do
	python $CRYPTOBIGBRO_PATH_TO_CODE/cryptobigbro.py fetch-ohlcv $EXCHANGE . --instruments ${i} --delay ${2}
done
git add *
git commit -a -m "Update OHLCV data."
git push -u origin master
