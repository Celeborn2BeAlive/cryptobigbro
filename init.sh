ROOTDIR=`dirname "$0"`
pushd $ROOTDIR
virtualenv venv
source venv/Scripts/activate
pip install -r requirements.txt