import React from 'react';
import { Slide, FlexBox, Heading, Text, Grid, Box, Image } from 'spectacle';
import Spotlight from '../components/react-bits/Spotlight';

const Slide5_Frontend = () => {
    // Placeholder for map image or component
    return (
        <Slide backgroundColor="tertiary">
            <FlexBox height="100%" flexDirection="column" alignItems="center">
                <Heading fontSize="h3" color="secondary" margin="0px 0px 30px 0px">
                    フロントエンドの工夫 (Mapbox + React)
                </Heading>

                <Grid gridTemplateColumns="1fr 1fr" gridGap={40} width="90%">
                    <Box>
                        <Spotlight className="rounded-xl border border-white/10 overflow-hidden bg-slate-800 p-4">
                            <Text fontSize="20px" color="secondary" className="mb-2">Map Component</Text>
                            <div className="h-48 bg-slate-700/50 rounded flex items-center justify-center text-slate-500">
                                Topological Data Visualization
                            </div>
                        </Spotlight>
                    </Box>
                    <Box className="flex flex-col justify-center">
                        <Heading fontSize="h5" color="quaternary">
                            状態管理の挑戦
                        </Heading>
                        <Text color="primary" fontSize="24px">
                            ・列車位置 (v4)<br />
                            ・ユーザーの「乗車予定」<br />
                            ・経路検索結果<br />
                        </Text>
                        <Text color="secondary" fontSize="24px" className="mt-4">
                     => これらを同期しつつ、60fpsのアニメーションを維持
                        </Text>
                    </Box>
                </Grid>
            </FlexBox>
        </Slide>
    );
};

export default Slide5_Frontend;
