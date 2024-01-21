"use strict";

const fs = require("fs");

const regexRoom = new RegExp("^([WE]{1})([0-9]{1,2})([NS]{1})([0-9]{1,2})$");

function isHighwayRoom(roomName) {
  const parsed = regexRoom.exec(roomName);
  if (parsed) {
    return parsed[2] % 10 === 0 || parsed[4] % 10 === 0;
  }
  return false;
}

fs.readFile("season_map_rawdata.json", (err, data) => {
  if (err) throw err;
  let map = JSON.parse(data);
  for (const roomData of map.rooms) {
    if (!isHighwayRoom(roomData.room)) {
      delete roomData.bus;
      delete roomData.depositType;
    }

    roomData.objects = roomData.objects.filter((o) => {
      if (o.type === "ruin") {
        return false;
      }
      if (o.type === "spawn") {
        return false;
      }
      if (o.type === "constructionSite") {
        return false;
      }
      return true;
    });

    for (const objectsData in roomData.objects) {
      if (objectsData.type === "controller") {
        objectsData.level = 0;
        delete objectsData.safeMode;
        delete objectsData.safeModeAvailable;
        delete objectsData.safeModeCooldown;
        delete objectsData.user;
        delete objectsData.isPowerEnabled;
        delete objectsData.downgradeTime;
        delete objectsData.progress;
        delete objectsData.progressTotal;
        delete objectsData.hits;
        delete objectsData.hitsMax;
      }
    }
  }

  fs.writeFile("season_map_clean.json", JSON.stringify(map), "utf8", (err) => {
    if (err) {
      throw err;
    }
    console.log("Complete");
  });
});
