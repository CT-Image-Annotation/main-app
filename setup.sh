rm -rf migrations
rm -rf instance

rm -rf uploads/*

flask db init
flask db migrate
flask db upgrade