from bson.code import Code
from mongo import get_db
from pprint import pprint
from json import dumps
from time import time

# collection: datum 
# produce aggregates for each selected indicator
# cat, time, country, user -> weight, value
# ___, time, country, user -> weight, value 
map_datum_to_aggregates = """function() {
    var meta_weights = %(meta_weights)s;
    var d = this; 
    %(weighting)s.items.forEach(function(i) {
        if (i[0] == d.indicator_id) {
            var value = (i[1]/100) * meta_weights[w.category] * d.value;
            emit({category: w.category, time: d.time, 
                  country: d.country, user_id: '%(user_id)s'},
                  value);
            emit({category: '__AXIS__', time: d.time,
                  country: d.country, user_id: '%(user_id)s'},
                  value); 
        }
    });}""" 

# collection: user_aggregates
# aggregate the per-user aggregates: 
# cat, time, country, ____ -> weight, value
# ___, time, country, ____ -> weight, value 
map_aggregates_to_aggregates = Code("""function() {
    emit({category: '__AXIS__', time: this._id.time,
          country: this._id.country, user_id: '__AXIS__'},
          this.value);
    emit({category: this._id.category, time: this._id.time, 
          country: this._id.country, user_id: '__AXIS__'},
          this.value);
}""")


# TODO: ask Guo about actual algorithm to be applied!  
reduce_aggregates = Code("""function(key, values) {
    var sum = 0; 
    values.forEach(function(v) { sum += v; });
    db.aggregates.update({"category" : key.category, 
                          "time" : key.time, 
                          "country" : key.country, 
                          "user_id" : key.user_id},
                          {'$set': {'value': sum}}, upsert=true); 
    return sum;
}""")

def update(db, user_id, weighting): 
    t0 = time() 
    meta_weights = {}
    #weightings = list(db.weighting.find({'user_id': user_id, }))
    #for weighting in user.get('weightings'): 
    #    if weighting.get('category') != 'meta':
    #        weightings.append(weighting)
    #    else: 
    #        for (category, weight) in weighting.get('items'): 
    #            meta_weights[category] = weight/100.0 

    values = {'user_id': user_id,
              'weighting': dumps(weighting), 
              'meta_weights': dumps(meta_weights)}
    map_function = Code(map_datum_to_aggregates % values)
    res = db.datum.map_reduce(map_function, 
                              reduce_aggregates, 
                              out='user_aggregates',
                              query={'indicator_id': {'$in': indicators},
                                     'year': 2007})
    print "USER", time()-t0

def update_global(db):
    t0 = time() 
    #  This can be done offline via CRON or something
    db.user_aggregates.map_reduce(map_aggregates_to_aggregates, 
                                  reduce_aggregates,
                                  out='global_aggregates')
    print "GLOBAL", time()-t0

# given a user


if __name__ == '__main__':
    db = get_db()
    ind = [
			"SPDYNIMRTIN",
			"SNITKSALTZS",
			"SHXPDPCAPPPKD",
			"SPDYNLE00IN",
			"SNITKDEFCZS",
			"SHDYNMORT"
		]
    update(db, 'd34408f2-ff85-43cd-afea-e086760fabaa', ind) 
    update_global(db)
