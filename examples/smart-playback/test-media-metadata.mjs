import assert from 'node:assert/strict';
import {SmartPlayer} from './eb-player.mjs';

globalThis.MediaMetadata=class{constructor(fields){Object.assign(this,fields);}};
globalThis.document={title:'Smart Play guide'};
const player=Object.assign(Object.create(SmartPlayer.prototype),{
 session:{metadata:null},sessionMetadata:null,
});

player.setMediaMetadata('  Smell  ');
assert.equal(player.session.metadata.title,'Smell');
player.clearMediaMetadata();
assert.equal(player.session.metadata,null);
player.setMediaMetadata('Energy Ball');
assert.equal(player.session.metadata.title,'Energy Ball');
const other=new MediaMetadata({title:'Another player'});
player.session.metadata=other;
player.clearMediaMetadata();
assert.equal(player.session.metadata,other,'do not clear metadata that another player set');
player.setMediaMetadata('');
assert.equal(player.session.metadata.title,'Smart Play guide');
document.title='  ';
player.setMediaMetadata();
assert.equal(player.session.metadata.title,'Open Consciousness Functions');
