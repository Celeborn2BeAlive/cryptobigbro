EXCHANGE=$1
cd $CRYPTOBIGBRO_PATH_TO_DATA/$EXCHANGE
# git pull # pull existing data
source $CRYPTOBIGBRO_PATH_TO_CODE/venv/bin/activate
python $CRYPTOBIGBRO_PATH_TO_CODE/cryptobigbro.py fetch-ohlcv $EXCHANGE .
# git add *
# git commit -a -m "Update OHLCV data"
# git push
