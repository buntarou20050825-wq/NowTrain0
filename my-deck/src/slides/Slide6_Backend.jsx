import React from 'react';
import { Slide, FlexBox, Heading, Text, UnorderedList, ListItem } from 'spectacle';

const Slide6_Backend = () => {
    return (
        <Slide backgroundColor="tertiary">
            <FlexBox height="100%" flexDirection="column" alignItems="center">
                <Heading fontSize="h3" color="secondary">
                    バックエンドの挑戦 (GTFS-RT)
                </Heading>
                <FlexBox flexDirection="row" justifyContent="space-around" width="100%" alignItems="start" className="mt-10">
                    <div className="w-1/2 p-4">
                        <Text color="quaternary" fontSize="32px" fontWeight="bold">Challenge</Text>
                        <Text color="primary">
                            GTFS-RTは「生のデータ」<br />
                            ・遅延情報しかない<br />
                            ・「今どこ？」は計算が必要
                        </Text>
                    </div>
                    <div className="w-1/2 p-4 border-l border-gray-600">
                        <Text color="secondary" fontSize="32px" fontWeight="bold">Solution (v4 Engine)</Text>
                        <UnorderedList>
                            <ListItem color="primary" fontSize="24px">
                                物理演算モデル (加速・減速・定速)
                            </ListItem>
                            <ListItem color="primary" fontSize="24px">
                                TripUpdate から「区間進捗率」を逆算
                            </ListItem>
                            <ListItem color="primary" fontSize="24px">
                                線路形状 (Shapes) への投影
                            </ListItem>
                        </UnorderedList>
                    </div>
                </FlexBox>
            </FlexBox>
        </Slide>
    );
};

export default Slide6_Backend;
