import React from 'react';
import { Slide, FlexBox, Heading, UnorderedList, ListItem, Appear } from 'spectacle';

const Slide4_Realtime = () => {
    return (
        <Slide backgroundColor="tertiary">
            <FlexBox height="100%" flexDirection="column" alignItems="flex-start" padding="0 10%">
                <Heading fontSize="h3" color="secondary">
                    リアルタイム性の仕組み
                </Heading>

                <UnorderedList>
                    <Appear>
                        <ListItem color="primary">
                            情報の「鮮度」が命<br />
                            <span className="text-base text-gray-400">-> ODPT APIから定期的に GTFS Realtime (TripUpdate) を取得</span>
                        </ListItem>
                    </Appear>
                    <Appear>
                        <ListItem color="primary">
                            物理演算補間 (v4 engine)<br />
                            <span className="text-base text-gray-400">-> データ更新間隔(1分)の間を、加速度・減速度を考慮して滑らかに補間</span>
                        </ListItem>
                    </Appear>
                    <Appear>
                        <ListItem color="primary">
                            Fetch戦略<br />
                            <span className="text-base text-gray-400">-> React Query (TanStack Query) ライクなポーリング管理</span>
                        </ListItem>
                    </Appear>
                </UnorderedList>
            </FlexBox>
        </Slide>
    );
};

export default Slide4_Realtime;
