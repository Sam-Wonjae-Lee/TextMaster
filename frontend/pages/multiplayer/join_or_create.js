import { useState, useEffect, useRef } from "react";
import React from "react";
import Sidebar from "@/components/side_bar";
import { useRouter } from "next/router";

const JoinOrCreate = () => {
    const [selectedButton, setSelectedButton] = useState(null);
    const headingRef = useRef(null);
    const [buttonWidth, setButtonWidth] = useState('auto');

    const router = useRouter();

    useEffect(() => {
        if (headingRef.current) {
            setButtonWidth(headingRef.current.offsetWidth);
        }
    }, []);

    const handleButtonClick = (buttonIndex) => {
        setSelectedButton(buttonIndex);
    };

    const handleJoinButton = () => {
        router.push('/multiplayer/rooms');
    };
    
    const handleCreateButton = () => {
        router.push('/multiplayer/create');
    };

    return (
        <div className="min-h-screen w-screen" style={{ display: 'flex' }}>
            <Sidebar selectedButton={selectedButton} handleButtonClick={handleButtonClick} buttonWidth={buttonWidth} />

            <div style={{ backgroundColor: '#FFFFFF', marginLeft: '20px', flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                <h1 className="text-4xl mt-5" style={{paddingTop:'20px'}}>Join Or Create Lobby</h1>

                <div className="mt-5 flex space-x-4" style={{gap: '140px', paddingTop: '130px'}}>
                    <button className="px-16 py-2 #4F46E5 text-white text-lg rounded" onClick={handleJoinButton} style={{padding: '40px', textAlign:"center"}}>Join</button>
                    <button className="px-16 py-4 #4F46E5 text-white text-lg rounded" onClick={handleCreateButton} style={{padding: '40px', textAlign: "center"}}>Create</button>
                </div>
            </div>
        </div>
    );
};

export default JoinOrCreate;