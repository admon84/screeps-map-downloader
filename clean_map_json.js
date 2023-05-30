'use strict';

const fs = require('fs');

fs.readFile('season_map_rawdata.json', (err, data) => {
    if (err) throw err;
    let map = JSON.parse(data);
    for (const r in map.rooms) {
        map.rooms[r].objects = map.rooms[r].objects.filter((o) => {
            if (o.type === 'ruin') {
                return false;
            }
            if (o.type === 'reactor') {
                return false;
            }
            if (o.type === 'spawn') {
                return false;
            }
            if (o.type === 'constructionSite') {
                return false;
            }
            if (o.type === 'mineral' && o.mineralType === 'T') {
                return false;
            }
            return true;
        });

        for (const o in map.rooms[r].objects) {
            if (map.rooms[r].objects[o].type === 'controller') {
                map.rooms[r].objects[o].level = 0;
                map.rooms[r].objects[o].safeMode = undefined;
                map.rooms[r].objects[o].safeModeAvailable = undefined;
                map.rooms[r].objects[o].safeModeCooldown = undefined;
                map.rooms[r].objects[o].user = undefined;
                map.rooms[r].objects[o].isPowerEnabled = undefined;
                map.rooms[r].objects[o].downgradeTime = undefined;
                map.rooms[r].objects[o].progress = undefined;
                map.rooms[r].objects[o].progressTotal = undefined;
                map.rooms[r].objects[o].hits = undefined;
                map.rooms[r].objects[o].hitsMax = undefined;
            }
        }
    }

    fs.writeFile('season_map_clean.json', JSON.stringify(map), 'utf8', (err) => {
        if (err) {
            throw err;
        }
        console.log('Finished');
    });
});