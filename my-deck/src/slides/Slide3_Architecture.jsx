import React from 'react';
import { Slide, FlexBox, Heading, Text, Image } from 'spectacle';
import Spotlight from '../components/react-bits/Spotlight';

const Slide3_Architecture = () => {
    return (
        <Slide backgroundColor="tertiary">
            <FlexBox height="100%" flexDirection="column" alignItems="center">
                <Heading fontSize="h3" color="secondary" margin="0px 0px 30px 0px">
                    全体アーキテクチャ
                </Heading>

                <Spotlight className="w-[80vw] h-[60vh] bg-slate-800/50 rounded-xl flex items-center justify-center p-8 border border-white/10">
                    {/* Diagram Placeholder - using Text for now, could be an image or mermaid */}
                    <div className="flex flex-row items-center justify-between w-full text-white">
                        <div className="p-4 bg-blue-900/50 rounded-lg border border-blue-500/30">
                            <Text fontSize="20px" color="secondary">Frontend (React)</Text>
                            <div className="text-sm text-gray-300">Mapbox GL JS</div>
                        </div>
                        <div className="h-px w-10 bg-gray-500 relative">
                            <div className="absolute top-[-10px] left-[10px] text-[10px] text-gray-400">HTTP</div>
                        </div>
                        <div className="p-4 bg-green-900/50 rounded-lg border border-green-500/30">
                            <Text fontSize="20px" color="secondary">Backend (FastAPI)</Text>
                            <div className="text-sm text-gray-300">GTFS-RT Handler</div>
                        </div>
                        <div className="h-px w-10 bg-gray-500 relative">
                            <div className="absolute top-[-10px] left-[10px] text-[10px] text-gray-400">Fetch</div>
                        </div>
                        <div className="p-4 bg-purple-900/50 rounded-lg border border-purple-500/30">
                            <Text fontSize="20px" color="secondary">External Data</Text>
                            <div className="text-sm text-gray-300">ODPT (GTFS-RT)</div>
                        </div>
                    </div>
                </Spotlight>
                <Text fontSize="16px" color="primary" className="mt-8">
                    ReactフロントエンドがFastAPI経由で正規化されたGTFS-RTデータを取得
                </Text>
            </FlexBox>
        </Slide>
    );
};

export default Slide3_Architecture;
