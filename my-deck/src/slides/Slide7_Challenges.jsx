import React from 'react';
import { Slide, FlexBox, Heading, Text, Box } from 'spectacle';
import DecayCard from '../components/react-bits/DecayCard';

const Slide7_Challenges = () => {
    return (
        <Slide backgroundColor="tertiary">
            <FlexBox height="100%" flexDirection="column" alignItems="center" justifyContent="center">
                <Heading fontSize="h3" color="secondary" margin="0px 0px 40px 0px">
                    苦労した点と解決策
                </Heading>

                <Box width="70%">
                    <DecayCard className="mb-8">
                        <Text color="quaternary" fontSize="28px" fontWeight="bold">Bug: 深夜の「幽霊列車」</Text>
                        <Text color="primary" fontSize="24px">
                            日跨ぎ（24時過ぎ）の時刻計算ミス。<br />
                            25:00 を 01:00 と誤解釈し、列車が過去へタイムスリップ。
                        </Text>
                        <div className="mt-4 border-t border-white/20 pt-2">
                            <Text color="secondary" fontSize="20px">
                        -> TimeManagerクラスで「仮想24時間制（30時間制）」を厳密に管理することで解決。
                            </Text>
                        </div>
                    </DecayCard>

                    <DecayCard>
                        <Text color="quaternary" fontSize="28px" fontWeight="bold">Perf: ブラウザのメモリリーク</Text>
                        <Text color="primary" fontSize="24px">
                            Mapboxのマーカーを毎回生成・破棄していた。
                        </Text>
                        <div className="mt-4 border-t border-white/20 pt-2">
                            <Text color="secondary" fontSize="20px">
                        -> マーカープール制（再利用）を導入し、GCの発生を抑制。
                            </Text>
                        </div>
                    </DecayCard>
                </Box>
            </FlexBox>
        </Slide>
    );
};

export default Slide7_Challenges;
