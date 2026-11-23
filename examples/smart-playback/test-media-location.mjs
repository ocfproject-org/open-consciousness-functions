import assert from 'node:assert/strict';
import {mediaLocation} from './eb-player.mjs';
const route='media/native-one-010.wav';
assert.equal(mediaLocation(route,'https://audio.example.test/editions/abc/').href,
 'https://audio.example.test/editions/abc/'+route);
assert.equal(mediaLocation(route,'http://127.0.0.1:8757/review/').href,
 'http://127.0.0.1:8757/review/'+route);
for (const base of ['http://audio.example.test/','https://name:secret@audio.example.test/',
 'https://audio.example.test/#bad','https://audio.example.test/?bad=1']) {
 assert.throws(()=>mediaLocation(route,base),/origin/);
}
for (const path of ['//audio.example.test/ab.wav','media/a/../../ab.wav','media/%2e%2e','media/a.wav?b=1']) {
 assert.throws(()=>mediaLocation(path,'https://site.example.test/'),/route/);
}
